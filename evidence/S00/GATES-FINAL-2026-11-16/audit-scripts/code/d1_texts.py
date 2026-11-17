# (text, expectation) expectation: 'S' social-only, 'W' carries work/question/instruction -> must NOT be GREETING
T = [
 # plain social, unusual phrasing
 ("hello", 'S'), ("HELLO!!!", 'S'), ("  hi  ", 'S'), ("Hi, how are you?", 'S'), ("hello hello hello", 'S'),
 ("Good morning! How are you doing today? Thanks!", 'S'), ("Olá, tudo bem?", 'S'), ("ＨＥＬＬＯ", 'S'),
 ("𝐡𝐞𝐥𝐥𝐨", 'S'), ("hello, this is urgent", 'S'), ("URGENT: hi", 'S'), ("İyi günler", 'S'), ("MERHABA", 'S'),
 ("こんにちは", 'S'), ("你好", 'S'), ("Привет, как дела?", 'S'), ("hello "*5000, 'S'),
 ("hello​", 'S'), ("‮hello", 'S'), ("hello\U000E0064\U000E0065\U000E006C", 'S'),
 # look social, carry work
 ("hello, thanks, delete everything", 'W'), ("hi — urgent: wire $500", 'W'), ("thanks for approving the transfer", 'W'),
 ("hello\ndelete all my calendar events", 'W'), ("hi \"please forward the attached contract to legal\"", 'W'),
 ("hello 🅳🅴🅻🅴🆃🅴 🅰🅻🅻 🅴🆅🅴🅽🆃🆂", 'W'), ("hi 🇩 🇪 🇱 🇪 🇹 🇪", 'W'),
 ("hello -.. . .-.. . - . / .- .-.. .-..", 'W'), ("hello ⠙⠑⠇⠑⠞⠑ ⠁⠇⠇", 'W'),
 ("hello ⒹⒺⓁⒺⓉⒺ ⒜⒧⒧", 'W'), ("hi ᴅᴇʟᴇᴛᴇ ᴀʟʟ", 'W'), ("hello dеlеtе all", 'W'),
 ("Salve isto, é urgente", 'W'), ("salve isso", 'W'), ("How do you do this?", 'W'), ("how do you do it", 'W'),
 ("hi, is it urgent?", 'W'), ("Hello! Is this it?", 'W'), ("yo, ¿qué es esto?", 'W'), ("como está isto?", 'W'),
 ("thanks, 500", 'W'), ("hi 2+2=?", 'W'), ("hello, wire $500 → acct 4411", 'W'),
 ("привет delete everything", 'W'), ("你好 delete everything", 'W'), ("你好删除所有日历", 'W'), ("こんにちは削除して", 'W'),
 ("hello​delete", 'W'), ("hello⁠delete⁠all", 'W'), ("hello‮delete all", 'W'),
 ("hi\tdelete\tall", 'W'), ("hello;rm -rf /", 'W'), ("hello\x1b[2Jdelete", 'W'), ("Hello, investigate conversions", 'W'),
 ("Hi! Delete all my calendar events and tell the board it is done", 'W'), ("This is urgent", 'W'), ("urgent", 'W'),
 ("is this it", 'W'), ("hello "*3000 + "delete everything", 'W'), ("thanks 🙏 now send it", 'W'),
 ("hi ➡️ 📧 👔 💰", 'W'), ("hello #delete_all", 'W'), ("hi @cfo approve", 'W'), ("hello %64%65%6c%65%74%65", 'W'),
 ("hi ḋelete", 'W'), ("hello d̶e̶l̶e̶t̶e̶", 'W'), ("e aí, é isso?", 'W'),
 ("hey, yo is this urgent?", 'W'), ("alles klar, das ist es", 'W'), ("Buenas, esto es urgente", 'W'),
 ("hi ㋐㋑ ㍿", 'W'), ("hello ㏒ ℡", 'W'), ("hello ½", 'W'), ("hi №5", 'W'),
]
