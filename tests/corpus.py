"""Realistic Chinese paragraphs used by the invariant tests.

Deliberately nasty: sentence punctuation at line edges, consecutive marks,
mixed Latin/CJK, numbers with units, brackets of every flavour, hard breaks,
an unbreakable URL, and one paragraph with no punctuation at all.
"""

CORPUS = [
    "他说：「这次不一样。」然后关掉了对话框。",
    "中文排版不是把字排整齐，而是让标点不去它不该去的地方。",
    "2026 年 11 月，GitHub 上最热的项目几乎都和 Agent Skills 有关。",
    "我用了三天时间，把《中文排版需求》里最痛的二十条规则实现了一遍。",
    "TODO: 这里需要补一个测试（大概吧）。",
    "如果你看到一行以「，」开头，那说明渲染器没有做断行禁则。",
    "Hello，world——这是一个中英混排的句子，数字 3.14 也在里面。",
    "价格是￥128.00，折扣 15%，截止到 12 月 31 日。",
    "（注：这句话里的括号是中文全角括号，不是英文括号。）",
    "第一行\n第二行\n第三行，换行是硬断行。",
    "……他说完就沉默了……………………",
    "「引用」『双引号』【方括号】〔六角括号〕《书名号》",
    "https://example.com/a/very/long/url/that/cannot/break",
    "这是一段没有任何标点的长句子用来测试纯汉字的贪心断行是否会溢出边界",
    "A B C D E F G H I J K L M N O P",
    "标点：，。！？；：、（）【】「」",
    "混合 English words 和中文，还有 123 数字。",
    "他说：“这句用的是弯引号。”然后走了。",
    "一行里只有一个字。",
    "重复的标点！！！！真的很多？？？？",
    "编号 1. 第一项\n编号 2. 第二项",
    "中文和 English 之间应该有一点点空隙。",
    "破折号——通常占两个字的位置。",
    "省略号……也是两个字。",
]

WIDTHS_EM = [6, 8, 10, 14, 20, 28]
