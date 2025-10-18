https://github.com/imas-tools/gakumas-master-translation

这是sunset作者的masterTrans仓库，主要流程就是你先把仓库fork成自己的，然后在本地仓库，用makefile的几个命令make update；make gen-todo；make merge。

make update是从远程https://github.com/vertesan/gakumasu-diff/这个仓库获取对比最新的diff文件，diff文件是每次游戏有更新开服以后才会更新，不像txt剧情那些可以提前预载提前解包。make update后有一个文件的第32万行的括号有问题，会报错，你找到那行，内容大概是“text:  （”，括号前面有个异常的全角空格，把这个空格删了就好了，再执行一次make update。

make gen-todo是会先把上一步update下来的/gakumasu-diff/orig生成一个新的/gakumasu-diff/json，然后对比/data目录下的json，会生成/pretranslate_todo/temp_key_cn和/pretranslate_todo/temp_key_jp两个目录，然后再对比找到jp有但cn没有的内容，生成在/pretranslate_todo/todo里，接下来要做的就是挨个翻译。
翻译完成以后将所有的json文件移动到/pretranslate_todo/todo/new里，在所有文件后面加上“_translated”，例如Achievement.json → Achievement_translated.json

make merge将上面提到的“_translated”和/gakumasu-diff/json以及/data已有的中文内容进行对比合并，然后生成在/pretranslate_todo/merged里，最后合并到/data中