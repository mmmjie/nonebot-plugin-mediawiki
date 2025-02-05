from typing import Optional

from nonebot import on_regex, on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import RawCommand

from . import config_manager
from .config import Config
from .data_source import Wiki
from .exception import NoDefaultPrefixException, NoSuchPrefixException
from .worker import *

# 接入帮助系统
__usage__ = '使用：\n' \
            '快速使用：wiki 前缀:条目名\n' \
            '[[前缀:条目名]] {{前缀:模板名}} ((前缀:条目名))\n' \
            '其中中括号、大括号匹配后会调用api搜索条目/模板名，如果有误，可以使用小括号方式绕过api直接生成链接\n' \
            '前缀由群管和bot超管配置，没有指定前缀或前缀无效时，会回落到默认前缀\n' \
            '配置（带global的是全局命令，仅超管可以使用）：\n' \
            '添加：wiki.add，wiki.add.global\n' \
            '删除：wiki.delete，wiki.delete.global\n' \
            '列表：wiki.list，wiki.list.global\n' \
            '设置默认：wiki.default，wiki.default.global\n' \
            '按提示提供相应参数即可\n' \
            '注意：私聊状态下该插件仅会响应超管的命令，且仅能管理全局wiki\n' \
            '完整文档请前往 https://github.com/KoishiMoe/nonebot-plugin-mediawiki 查看'

__help_version__ = '0.1.2'

__help_plugin_name__ = 'Wiki推送'

# 用于正则匹配的模板字符串
ARTICLE_RAW = r"&#91;&#91;(.*?)&#93;&#93;"  # adapter出于安全原因会把中括号转义，此处用于让事件响应器能正确响应事件
ARTICLE = r"\[\[(.*?)\]\]"
TEMPLATE = r"\{\{(.*?)\}\}"
RAW = r"\(\((.*?)\)\)"

# 响应器
wiki = on_regex(ARTICLE_RAW, permission=GROUP)
wiki_template = on_regex(TEMPLATE, permission=GROUP)
wiki_raw = on_regex(RAW, permission=GROUP)
wiki_quick = on_command("wiki ", permission=GROUP, priority=2)  # 设个更低的优先级，省着和设置管理器抢（虽然似乎不设也不会抢2333


@wiki.handle()
async def _wiki(bot: Bot, event: GroupMessageEvent):
    await wiki_process(bot, event, wiki, is_template=False)


@wiki_template.handle()
async def _wiki_template(bot: Bot, event: GroupMessageEvent):
    await wiki_process(bot, event, wiki_template, is_template=True)


@wiki_raw.handle()
async def _wiki_raw(bot: Bot, event: GroupMessageEvent):
    special, result = await wiki_parse(RAW, False, True, bot, event)
    await bot.send(event, result)


@wiki_quick.handle()
async def _wiki_quick(bot: Bot, event: GroupMessageEvent, raw_command: Optional[str] = RawCommand()):
    if raw_command and raw_command.endswith("wiki "):  # 防止选择式的消息及无关消息被误加括号
        message = str(event.message).strip().removeprefix(raw_command).strip()
        event2 = event.copy()  # 浅拷贝一下，省着篡改消息后把其他插件弄懵了～
        event2.message = Message("[[" + message + "]]")
        await wiki_process(bot, event2, wiki_quick, is_template=False)
    else:
        await wiki_process(bot, event, wiki_quick, is_template=False)
