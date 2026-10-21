"""
Red-Blood worldbuilding candidate evaluator.
Converts extracted entities into candidates and assesses disposition according to AGENTS.md rules.
"""

import hashlib
from typing import List, Dict, Any

from .schema import CandidateRecord
from .db import MiningDatabase
from .extractor import ChapterExtractor

# Evaluation mapping for Mushenji entities to Red-Blood universe
EVALUATION_SPECS = [
    {
        "name": "镇村石像",
        "category": "器物",
        "destination": "专项评估",
        "reason": "涉及大范围被动驱魔结界，需结合赤血世界的「地脉阳燧法器」与「先民镇瘴石俑」机制，核定反噬与地脉耗竭代价，防止破坏禁区仙凡瘴平衡。",
        "target_spec_path": "世界/器物/AGENTS.md",
        "adaptation": {
            "proposed_name": "镇夜古祠石俑",
            "tier": "百炼灵器 / 通灵玄器（受地脉品阶约束）",
            "origin": "上古先民或古仙庭遗留之地脉镇物",
            "red_blood_mechanics": "借由地脉深处的纯阳炽火流对冲死气，在幽冥阴瘴降临时代替血肉之躯承受阴煞侵蚀；反噬在于石体逐步受煞毒钙化崩解，不可脱离地脉枢纽移动。",
        },
    },
    {
        "name": "柳条婴儿篮",
        "category": "日用百艺",
        "destination": "仅留场景素材",
        "reason": "凡人江河漂流日用器物，缺乏独立法理与历史深度，适宜作为叙事场景背景细节，不建议单独建立设定词条。",
        "target_spec_path": "世界/器物/AGENTS.md",
        "adaptation": {
            "proposed_name": "避水柳编摇篮",
            "tier": "凡民百艺造物",
            "origin": "江河流域渔民以防腐桐油与韧柳编织之物",
            "red_blood_mechanics": "以凡俗百艺涂刷树胶阻水，不具备灵性反噬与神异流转。",
        },
    },
    {
        "name": "大墟黑夜",
        "category": "异类材料",
        "destination": "专项评估",
        "reason": "与赤血已有的「仙凡瘴」及「禁地深处幽冥死潮」法理高度相关，需与《世界/背景/仙凡瘴.md》严格对齐，不可另立冲突的夜间天灾体系。",
        "target_spec_path": "世界/禁地/AGENTS.md",
        "adaptation": {
            "proposed_name": "幽冥死瘴夜潮",
            "tier": "天地绝地天象",
            "origin": "荒古崩坏时沉入地底的地煞阴脉在阳气衰微时上涌",
            "red_blood_mechanics": "入夜时阴脉蒸腾，化作吞噬气血神魂的黑瘴死潮；唯有纯阳灵火、特定古祭坛力场及帝网敕封明光可予阻遏。",
        },
    },
    {
        "name": "四灵血",
        "category": "丹药",
        "destination": "优先转化",
        "reason": "经典四大灵兽本源精血合炼洗髓模型，认知度高，易于原生融入赤血的百艺药道与四象地脉灵兽体系。",
        "target_spec_path": "世界/草木/AGENTS.md",
        "adaptation": {
            "proposed_name": "四象淬脉灵血散",
            "tier": "二品至三品淬体秘药",
            "origin": "采九州大泽中具有上古四灵遗泽的异兽本命精血",
            "red_blood_mechanics": "以四象五行生克调理周天经脉，行药时必须伴随极寒灵泉平抑燥烈血火，否则必遭心火焚脉反噬。",
        },
    },
    {
        "name": "母兽灵乳",
        "category": "草木",
        "destination": "仅留场景素材",
        "reason": "温和滋补之物，功能单一，建议作为丹师调配猛烈药剂或宗族豢养幼童的配角素材留存。",
        "target_spec_path": "世界/草木/AGENTS.md",
        "adaptation": {
            "proposed_name": "灵鹿温润甘乳",
            "tier": "凡阶上乘灵泉饮料",
            "origin": "驯化异兽在哺乳期所产富含草木温气的汁液",
            "red_blood_mechanics": "专用于中和燥烈金石丹砂之毒性，润泽脾胃。",
        },
    },
    {
        "name": "残腿神行法",
        "category": "术法",
        "destination": "优先转化",
        "reason": "以残缺之躯借外物拐杖爆发缩地腾挪的经典身法，意境独特且具武道玄门质感，非常契合赤血凡俗高修的法门体系。",
        "target_spec_path": "世界/功法/法术/AGENTS.md",
        "adaptation": {
            "proposed_name": "铁杖缩地身法",
            "tier": "黄阶上乘武修身法 / 灵动遁术",
            "origin": "凡俗武道宗师或断足散修所创借力破空之术",
            "red_blood_mechanics": "起势需将元气凝聚于杖尖一点破土借力，行法如燕掠波，收势沉气入腹；反噬为下肢承重关节经脉长久易损。",
        },
    },
    {
        "name": "天魔造化功",
        "category": "术法",
        "destination": "专项评估",
        "reason": "涉及人体形意实时重塑与微观血肉操纵，直接关联赤血世界的「形意实时对流」核心底层法理，必须严谨设定因果代价与反噬边界。",
        "target_spec_path": "世界/功法/法术/AGENTS.md",
        "adaptation": {
            "proposed_name": "形意易髓造化诀",
            "tier": "地阶下品魔门秘术",
            "origin": "上古形意魔宗勘破肉身虚妄所创移形换相之法",
            "red_blood_mechanics": "施术者强行打碎自身皮膜骨骼形貌以神识重塑；若维持超过三个时辰，形神失调，肉身骨骼将发生畸形异变导致业力加身。",
        },
    },
    {
        "name": "灵草接骨藤",
        "category": "草木",
        "destination": "优先转化",
        "reason": "典型凡人流外用疗伤草药，交代水土性味后可直接丰富赤血九州灵植生态与散修采药行当。",
        "target_spec_path": "世界/草木/AGENTS.md",
        "adaptation": {
            "proposed_name": "幽岩缠玉续断藤",
            "tier": "一阶灵植草木",
            "origin": "生长于潮湿阴崖缝隙，吸纳微弱玉石地气而生",
            "red_blood_mechanics": "性甘微苦温，汁白如乳，捣碎外敷能在一昼夜内促使断骨交生骨茧；采摘需以木刀割取，忌金铁锈气。",
        },
    },
    {
        "name": "刺穴银针",
        "category": "器物",
        "destination": "优先转化",
        "reason": "医道与截脉百艺利器，属于低阶灵器器具，易于规范入库。",
        "target_spec_path": "世界/器物/AGENTS.md",
        "adaptation": {
            "proposed_name": "渡灵透穴玄银针",
            "tier": "下品凡器 / 百炼灵器",
            "origin": "以沉银与微量秘银淬火拉丝锻成",
            "red_blood_mechanics": "能顺畅传导微弱元气破开护体罡气刺入气穴；若刺中死穴引气失控，受刺者气血逆流爆裂。",
        },
    },
    {
        "name": "漓江青锋剑",
        "category": "器物",
        "destination": "优先转化",
        "reason": "经典宗门制式低阶飞剑，完美对应赤血器物六阶之「百炼灵器」，可作为江河水系门派的量产兵器模板。",
        "target_spec_path": "世界/器物/AGENTS.md",
        "adaptation": {
            "proposed_name": "青澜破风飞刃",
            "tier": "百炼灵器（二阶）",
            "origin": "水道仙门百艺坊制式锻造",
            "red_blood_mechanics": "铭刻破水飞空云纹，筑基或开脉圆满修士以剑诀牵引可十丈内飞斩；反噬在于剑身材质单薄，硬碰真形道器瞬息崩断。",
        },
    },
    {
        "name": "漓江御气剑法",
        "category": "术法",
        "destination": "优先转化",
        "reason": "入门级行气剑芒法术，源流清晰，适合归入九州宗派基础法术库。",
        "target_spec_path": "世界/功法/法术/AGENTS.md",
        "adaptation": {
            "proposed_name": "叠浪分流剑气术",
            "tier": "黄阶下品基础剑法",
            "origin": "江流门派观大水奔涌所创气剑法门",
            "red_blood_mechanics": "起势引气入腕，行法化作三尺水色剑芒连绵刺杀，收势还剑入鞘；反噬为连出十剑后经脉酸胀刺痛，易脱力。",
        },
    },
    {
        "name": "解牛剔骨刀",
        "category": "器物",
        "destination": "优先转化",
        "reason": "重型煞刃兵器，契合赤血世界中以百兽凶煞之气养刀的旁门器物范式。",
        "target_spec_path": "世界/器物/AGENTS.md",
        "adaptation": {
            "proposed_name": "断兽分筋煞刃",
            "tier": "百炼灵器（附带煞气）",
            "origin": "屠宰荒原巨兽之宗匠历经甲子血浸而成",
            "red_blood_mechanics": "重三十六斤，刃不加饰，自带破甲分肉之锐；反噬为持刀者长期受凶兽临死怨煞反扑，需饮烈酒或修清心诀克制。",
        },
    },
    {
        "name": "换皮保形露",
        "category": "丹药",
        "destination": "优先转化",
        "reason": "偏门易容防腐药水，功能明确且代价显著，契合赤血暗门刺客与易容伪装的百艺法门。",
        "target_spec_path": "世界/草木/AGENTS.md",
        "adaptation": {
            "proposed_name": "凝肌锁形腐生液",
            "tier": "二阶偏门秘药",
            "origin": "采幽泽苔藓与蛇蜕精粹提炼",
            "red_blood_mechanics": "浸泡灵皮可保三年柔软如生；贴面使用过频者，面部皮肤气孔萎缩失去触觉感知。",
        },
    },
    {
        "name": "醉仙软筋散",
        "category": "丹药",
        "destination": "优先转化",
        "reason": "经典江湖与低阶修仙迷药，代价与解法完备，可作为行脚防身与刺杀的场景常用品。",
        "target_spec_path": "世界/草木/AGENTS.md",
        "adaptation": {
            "proposed_name": "散气滞脉迷梦粉",
            "tier": "一阶偏门毒散",
            "origin": "以梦罗花与醉仙藤研磨调配",
            "red_blood_mechanics": "气味微甘，入体麻痹元气运转三炷香；解法需服食清灵薄荷丹或由高阶修士渡气冲关逼出。",
        },
    },
    {
        "name": "避魔兽骨明灯",
        "category": "器物",
        "destination": "优先转化",
        "reason": "荒野夜行不可或缺的凡人与低阶修士防护器物，非常符合大界禁区生存感。",
        "target_spec_path": "世界/器物/AGENTS.md",
        "adaptation": {
            "proposed_name": "辟瘴照夜颅骨灯",
            "tier": "下品凡器 / 百炼灵器",
            "origin": "取大泽辟火角兽颅骨凿空为盏，注入灵兽凝脂",
            "red_blood_mechanics": "灯火呈淡金色，能照彻周围一丈避开微弱阴瘴；反噬为消耗极快，每盏油尽灯枯即失去防护。",
        },
    },
]


class CandidateEvaluator:
    def __init__(self, db: MiningDatabase):
        self.db = db

    def evaluate_candidates(self, source_id: str = "mushenji_v1") -> List[CandidateRecord]:
        extractor = ChapterExtractor(self.db)
        extractor.rebuild_entities(source_id)
        entities = self.db.get_all_entities(source_id)
        # Templates are proposals, not evidence or automatic world-rule checks.
        # Revalidate source hashes at use time, even after semantic approval.
        eligible = []
        for entity in entities:
            if entity["status"] != "verified" or not entity["claims"]:
                continue
            for claim in entity["claims"]:
                extractor.check_evidence(source_id, claim)
                if not claim.get("reviewer") or not claim.get("review_note"):
                    raise ValueError("Verified claim lacks a semantic review record")
            eligible.append(entity)
        entities = eligible
        entity_dict = {(e["canonical_name"], e["category"]): e for e in entities}

        candidates: List[CandidateRecord] = []
        for spec in EVALUATION_SPECS:
            name = spec["name"]
            ent = entity_dict.get((name, spec["category"]))
            if not ent:
                continue

            cand_id = f"cand_{ent['entity_id']}"
            candidate = CandidateRecord(
                candidate_id=cand_id,
                entity_id=ent["entity_id"],
                canonical_name=name,
                category=spec["category"],
                destination=spec["destination"],
                reason="[预设转化建议，未完成仓库检索与法理审校] " + spec["reason"],
                target_spec_path=spec["target_spec_path"],
                proposed_adaptation=spec["adaptation"],
            )
            candidates.append(candidate)

        self.db.save_candidates(candidates)
        return candidates
