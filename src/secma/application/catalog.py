"""SCS definitions and executable bindings stay distinct. No dynamic code loading."""
import copy
from dataclasses import dataclass, field
from hashlib import sha256
import json
import re

from jsonschema import Draft202012Validator
from secma.behavior.validated_reference import validate_schema
from secma.domain.policy import Principal, Policy


def canonical_hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


@dataclass
class Catalog:
    definitions: dict = field(default_factory=dict)
    bindings: dict = field(default_factory=dict)
    handlers: dict = field(default_factory=dict)

    def register(self, definition, binding, handler):
        validate_schema(definition, 'scs-capability.schema.json')
        validate_schema(binding, 'agent-binding.schema.json')
        if definition['id'] in self.definitions:
            raise ValueError('Duplicate capability ID')
        if binding['capability_id'] != definition['id'] or binding['capability_version'] != definition['version']:
            raise ValueError('Binding identity mismatch')
        self.definitions[definition['id']] = copy.deepcopy(definition)
        self.bindings[definition['id']] = copy.deepcopy(binding)
        self.handlers[binding['implementation_ref']] = handler


class CatalogSession:
    """One request, trusted principal, bounded candidate list and actual outputs."""
    def __init__(self, catalog, principal, policy):
        self.catalog, self.principal, self.policy = catalog, principal, policy
        self.events, self.results = [], []

    def _authorized(self, capability_id):
        definition = self.catalog.definitions.get(capability_id)
        binding = self.catalog.bindings.get(capability_id)
        if not definition or not binding or not self.policy or not self.policy.authorize(self.principal, definition, binding):
            raise PermissionError('Capability unavailable or denied by trusted policy')
        if binding['implementation_ref'] not in self.catalog.handlers:
            raise PermissionError('No registered executable binding')
        return definition, binding

    def search(self, query: str):
        if not isinstance(query, str) or len(query) > 2000:
            raise ValueError('Search query must be bounded text')
        words = set(re.findall(r'\w+', query.lower()))
        results = []
        for ident in self.catalog.definitions:
            try:
                definition, binding = self._authorized(ident)
            except PermissionError:
                continue
            corpus = definition['description'].lower() + ' ' + ' '.join(definition['intents']['positive_examples']).lower()
            score = sum(word in corpus for word in words)
            results.append((score, {'id': ident, 'name': definition['name'], 'description': definition['description'],
                                     'effects': definition['effects'], 'assurance': 'LOCAL_FIXTURE_ONLY'}))
        found = [entry for _, entry in sorted(results, key=lambda item: (-item[0], item[1]['id']))[:5]]
        self.events.append({'tool':'search', 'query_hash':canonical_hash(query), 'result_ids':[v['id'] for v in found]})
        return found

    def describe(self, capability_id: str):
        definition, _ = self._authorized(capability_id)
        self.events.append({'tool':'describe', 'capability_id':capability_id})
        return copy.deepcopy(definition)

    def invoke(self, capability_id: str, arguments: dict):
        try:
            definition, binding = self._authorized(capability_id)
        except PermissionError:
            self.events.append({'tool':'invoke', 'status':'DENIED', 'capability_id_hash':canonical_hash(capability_id)})
            raise
        try:
            Draft202012Validator(definition['input_schema']).validate(arguments)
        except Exception as exc:
            raise ValueError('Capability input violates its contract') from exc
        self.events.append({'tool':'invoke', 'capability_id':capability_id, 'arguments_hash':canonical_hash(arguments),
                            'policy_version':self.policy.version, 'status':'AUTHORIZED'})
        result = self.catalog.handlers[binding['implementation_ref']](copy.deepcopy(arguments))
        try:
            Draft202012Validator(definition['output_schema']).validate(result)
        except Exception as exc:
            raise ValueError('Capability output violates its contract') from exc
        self.results.append(copy.deepcopy(result))
        self.events.append({'tool':'result', 'capability_id':capability_id, 'result_hash':canonical_hash(result), 'status':'FIXTURE_RESULT'})
        return result


def fixture_catalog():
    catalog = Catalog()
    for domain, description, positive, negative, finding in [
        ('incident', 'Inspect synthetic operational incident logs for conversion failures and timing. Does not estimate causal treatment effects.',
         ['Investigate conversion failures in incident logs', 'Inspect error timing and deployment evidence'],
         ['Estimate campaign causal treatment effects'], 'Synthetic log contains an error spike; cause remains unproven.'),
        ('causal', 'Inspect synthetic campaign experiment evidence for conversion treatment effects and confounding. Does not diagnose operational incident logs.',
         ['Examine campaign conversion treatment effects', 'Check experiment confounding and assignment'],
         ['Inspect deployment error logs'], 'Synthetic observational difference is not identified as a causal effect.')]:
        ident = 'secma.fixture.' + domain
        definition = {'schema_version':'scs/1.0','id':ident,'version':'1.0.0','name':domain.title()+' fixture review',
                      'description':description,'intents':{'positive_examples':positive,'negative_examples':negative},
                      'input_schema':{'type':'object','required':['question'],'properties':{'question':{'type':'string','minLength':1,'maxLength':2000}},'additionalProperties':False},
                      'output_schema':{'type':'object','required':['status','source_classification','finding','evidence_refs'],
                                       'properties':{'status':{'const':'FIXTURE_RESULT'},'source_classification':{'const':'synthetic'},
                                                     'finding':{'type':'string'},'evidence_refs':{'type':'array','minItems':1,'items':{'type':'string'}}},'additionalProperties':False},
                      'outcomes':{'criteria':['Return explicitly synthetic evidence and limitations']},'permissions':['fixture:read'],
                      'effects':'read','requires_approval':False,'dependencies':[],'lifecycle':'enabled','assurance':'C2',
                      'evaluation':['tests/unit/test_runtime.py::test_m15_discovery_and_output_are_actual_fixtures']}
        binding = {'schema_version':'scs-binding/1.0','id':ident+'.binding','capability_id':ident,'capability_version':'1.0.0',
                   'adapter_type':'mock','implementation_ref':'fixture.'+domain+'.v1','enabled':True,'requirements':[], 'verification':'LOCAL'}
        def handler(arguments, finding=finding, domain=domain):
            return {'status':'FIXTURE_RESULT','source_classification':'synthetic','finding':finding,
                    'evidence_refs':['fixture:'+domain+':1:'+canonical_hash(finding)]}
        catalog.register(definition, binding, handler)
    return catalog
