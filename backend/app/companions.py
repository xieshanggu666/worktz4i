from __future__ import annotations

import random

# 伙伴模块（规则 2.6.0）：
# 玩家在旅途商店花金币招募一名伙伴，招募后可在「随行」与「休整」之间切换；
# 随行伙伴进入战斗——每个自己的回合开始时按其特性协助攻击（独立结算事件，
# 走结算队列，因此易伤/易碎加成、死亡打断、收尾击杀与胜负都在同一套规则里）；
# 敌人带有「重创」（wound）标记的攻击在突破格挡削到玩家生命时会让随行伙伴
# 负伤（hp-1，归零即暂停参战），负伤伙伴只能在休息节点治疗（每场休息一次，
# 回满并立即恢复随行）。伙伴状态（含伤势）保存在 run 状态并随章节交接快照
# 跨章继承，招募扣款/战斗协助/负伤/治疗全部是动作序列的确定性函数——
# 续局、整局回放与旧档迁移（缺字段补空名单）天然逐位一致。

ACCOMPANY = "accompany"   # 随行：进入战斗并协助
REST = "rest"            # 休整：保留在名册中但不参战
MODES = (ACCOMPANY, REST)

# 商店每格最多挂出的伙伴货架项（仅未拥有的；同局永不重复挂出已招募的同型）
OFFER_COUNT = 2

# 伙伴类型定义：assist 为每回合开始的协助效果（与卡牌/药水效果同构，
# 由结算队列统一解释，source="companion"）；hp 为生命值（即可承受的重创数）。
COMPANIONS: dict[str, dict] = {}


def _companion(cid, name, title, hp, price, desc, assist, icon="🐾"):
    COMPANIONS[cid] = {
        "id": cid, "name": name, "title": title, "hp": hp, "price": price,
        "desc": desc, "assist": [dict(e) for e in assist], "icon": icon,
    }


_companion("kunoichi", "忍猫", "见习忍猫", 2, 55,
           "随行时每个自己的回合开始对敌人造成 3 点伤害（攻击标签，可触发其回响）。",
           [{"type": "damage", "value": 3, "target": "enemy", "tags": ["attack"]}],
           icon="🐱")
_companion("squire", "侍从", "见习侍从", 3, 60,
           "随行时每个自己的回合开始为你获得 4 点格挡，并对敌人造成 2 点伤害。",
           [{"type": "gain_block", "value": 4, "target": "player"},
            {"type": "damage", "value": 2, "target": "enemy", "tags": ["attack"]}],
           icon="🛡️")
_companion("mystic", "学徒法师", "奥术学徒", 1, 45,
           "随行时每个自己的回合开始对敌人造成 5 点伤害（术法伤害，不挂攻击标签）。",
           [{"type": "damage", "value": 5, "target": "enemy"}],
           icon="🔮")


def get_companion(cid):
    c = COMPANIONS.get(cid)
    if c is None:
        raise KeyError(f"unknown companion: {cid}")
    return dict(c)


def all_companions():
    return [dict(v) for v in COMPANIONS.values()]


def public_companion(cid):
    """货架/目录用的只读元数据。"""
    c = COMPANIONS[cid]
    return {"id": cid, "name": c["name"], "title": c["title"], "desc": c["desc"],
            "price": c["price"], "hp": c["hp"], "icon": c["icon"]}


def generate_offers(stock_seed, owned_ids):
    """确定性生成商店伙伴货架：从尚未招募的伙伴中抽取（每个货架项独立 sold）。

    只依赖 (stock_seed, 进入时的已招募集合)；拥有集合本身由动作序列确定性派生，
    因此同一条动作日志重放必得同一组货架。已招募满全员则不再挂出。
    """
    rng = random.Random((stock_seed * 19 + 23) & 0xFFFFFFFF)
    ids = sorted(cid for cid in COMPANIONS if cid not in set(owned_ids))
    rng.shuffle(ids)
    return [{
        "sku": f"companion:{cid}", "kind": "companion", "companion": cid,
        "price": COMPANIONS[cid]["price"], "sold": False,
    } for cid in ids[:OFFER_COUNT]]


def offer_view(item):
    c = COMPANIONS[item["companion"]]
    return {**item, "name": c["name"], "title": c["title"], "desc": c["desc"],
            "icon": c["icon"], "hp": c["hp"]}


def make_companion(cid):
    """招募：新伙伴实例（满血；首次招募且当前没有随行伙伴时默认随行）。"""
    c = COMPANIONS[cid]
    return {"id": cid, "hp": c["hp"], "max_hp": c["hp"], "mode": REST}


def is_wounded(c):
    """负伤（暂停参战）：hp 低于其生命上限。"""
    return c.get("hp", c.get("max_hp", 0)) < c.get("max_hp", 0)


def active_companion(companions):
    """返回当前随行且未负伤的伙伴实例（战斗中协助的那位）；否则 None。"""
    for c in companions or []:
        if c.get("mode") == ACCOMPANY and not is_wounded(c):
            return c
    return None


def companion_public(c):
    """伙伴名册的只读视口（侧栏/回放共用）。"""
    defn = COMPANIONS.get(c["id"], {})
    return {
        "id": c["id"], "name": defn.get("name", c["id"]),
        "title": defn.get("title", ""), "icon": defn.get("icon", "🐾"),
        "desc": defn.get("desc", ""),
        "hp": c.get("hp", 0), "max_hp": c.get("max_hp", defn.get("hp", 0)),
        "mode": c.get("mode", REST),
        "wounded": is_wounded(c),
        "accompanying": c.get("mode") == ACCOMPANY and not is_wounded(c),
    }


def roster_public(companions):
    return [companion_public(c) for c in companions or []]
