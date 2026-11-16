from h import *
ready('p0')
print(model('p0', [['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']], 'ask','Find my next appointment','--json')[0])
r=q('p0','ask','hello','--json'); print(r[0], brief(r[1]))
