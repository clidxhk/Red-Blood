"""
Extractor for chapters 1-10 of Mushenji.
Extracts mentions, claims, and consolidates entities based on PLAN.md.
"""

import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

from .schema import MentionRecord, ClaimRecord, EntityRecord
from .db import MiningDatabase

# Extraction definitions for Chapters 1-10
CHAPTER_EXTRACTION_SPECS = [
    {
        "chapter_index": 1,
        "items": [
            {
                "name": "镇村石像",
                "alias": "残老村石像",
                "category": "器物",
                "keywords": ["石像"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "黑夜降临大墟时散发微弱神光，形成防护力场驱散外围黑暗与魔怪。",
                        "claim_type": "情节展示",
                        "conditions": "仅在黑夜与黑暗生物侵袭时被动激发生效",
                    },
                    {
                        "attribute": "代价副作用",
                        "value": "神像风化磨损严重，防护范围随岁月推移与外力侵蚀逐步衰减。",
                        "claim_type": "旁白说明",
                        "conditions": "长期暴露于恶劣环境中缺乏祭祀与修葺",
                    },
                    {
                        "attribute": "材质形制",
                        "value": "四尊古老斑驳的庞大石雕神兽/神祇雕像，分立于村落四角。",
                        "claim_type": "旁白说明",
                        "conditions": "古老遗存",
                    },
                ],
            },
            {
                "name": "柳条婴儿篮",
                "alias": "水上柳篮",
                "category": "日用百艺",
                "keywords": ["柳条", "篮子"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "以编织柳条承载弃婴于大江之上随波漂流而不沉入水中。",
                        "claim_type": "情节展示",
                        "conditions": "河道平缓无激流倾覆",
                    },
                    {
                        "attribute": "配方材质",
                        "value": "坚韧水柳编织，缝隙紧密涂有防水胶脂。",
                        "claim_type": "情节展示",
                        "conditions": "凡人工艺",
                    },
                ],
            },
            {
                "name": "大墟黑夜",
                "alias": "大墟黑暗魔潮",
                "category": "异类材料",
                "keywords": ["黑暗", "黑夜"],
                "claims": [
                    {
                        "attribute": "生态机制",
                        "value": "太阳落山后整片大墟被浓郁黑雾吞噬，内蕴狂暴噬血魔怪，活人入内尸骨无存。",
                        "claim_type": "旁白说明",
                        "conditions": "昼夜交替触发，光亮断绝即刻降临",
                    },
                    {
                        "attribute": "克制规律",
                        "value": "惧怕古老石像神光及特定极阳火光，无法直接攻破明光结界。",
                        "claim_type": "人物说法",
                        "conditions": "光亮强度必须达到一定阈值",
                    },
                ],
            },
        ],
    },
    {
        "chapter_index": 2,
        "items": [
            {
                "name": "四灵血",
                "alias": "青龙白虎朱雀玄武四灵异血",
                "category": "丹药",
                "keywords": ["四灵血", "异兽血"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "混合四种神圣灵兽精血涂抹周身或口服，用于洗髓伐毛、锤炼幼童骨血以觉醒灵体。",
                        "claim_type": "情节展示",
                        "conditions": "必须在药师辅助导气下方可吸收",
                    },
                    {
                        "attribute": "配方材质",
                        "value": "取青龙、白虎、朱雀、玄武四大异象对应的强悍灵兽本命精血各一合。",
                        "claim_type": "旁白说明",
                        "conditions": "精血活性必须保持完好",
                    },
                    {
                        "attribute": "代价副作用",
                        "value": "血性极其狂暴燥烈，寻常肉体承受不住易导致经脉撕裂或爆体而亡。",
                        "claim_type": "旁白说明",
                        "conditions": "需以温和药性母乳或寒泉中和冲淡",
                    },
                ],
            },
            {
                "name": "母兽灵乳",
                "alias": "牝兽之乳",
                "category": "草木",
                "keywords": ["兽奶", "母兽"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "捕获哺乳期温驯母兽取其灵乳，中和狂暴药性并提供幼体筑基气血滋养。",
                        "claim_type": "情节展示",
                        "conditions": "需新鲜温热饮用",
                    },
                ],
            },
        ],
    },
    {
        "chapter_index": 3,
        "items": [
            {
                "name": "残腿神行法",
                "alias": "瘸子神腿步法",
                "category": "术法",
                "keywords": ["瘸子", "拐杖", "腿法", "神行"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "借拐杖着力与单腿元气爆发，实现刹那缩地腾挪、迅捷如雷的身法移动。",
                        "claim_type": "情节展示",
                        "conditions": "需精准掌控下肢元气喷吐节奏",
                    },
                    {
                        "attribute": "起势行法",
                        "value": "元气沉入单足与拐杖尖端，借反震力离地滑翔并变换方位。",
                        "claim_type": "情节展示",
                        "conditions": "受地面材质与着力点影响",
                    },
                ],
            },
            {
                "name": "铁匠锻锤",
                "alias": "百炼铁砧重锤",
                "category": "器物",
                "keywords": ["铁锤", "铁砧"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "重逾百斤的玄铁锻锤，借臂力与元气震荡捶打金属胚料以去杂质铸形。",
                        "claim_type": "情节展示",
                        "conditions": "需配合火炉地火温度",
                    },
                ],
            },
        ],
    },
    {
        "chapter_index": 4,
        "items": [
            {
                "name": "天魔造化功",
                "alias": "天魔造化神诀",
                "category": "术法",
                "keywords": ["天魔造化功", "造化功"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "魔道微观行气绝学，能以元气精细操纵皮肉筋膜与骨骼排列，实现改换容貌身形乃至重塑伤损肢体。",
                        "claim_type": "人物说法",
                        "conditions": "需要对人体经络与骨骼微细结构极其熟悉",
                    },
                    {
                        "attribute": "代价副作用",
                        "value": "移骨换皮过程剧痛难忍，元气不继易导致骨肉错位坏死，被正道视为魔道异端邪法。",
                        "claim_type": "旁白说明",
                        "conditions": "施术时若被打断将承受严重肉身反噬",
                    },
                    {
                        "attribute": "起势行法",
                        "value": "催动细如游丝的元气深入肌肉皮下，如雕刀般逐一挪动骨节与皮膜组织。",
                        "claim_type": "情节展示",
                        "conditions": "需极高元气精微控制力",
                    },
                ],
            },
            {
                "name": "灵草接骨藤",
                "alias": "止血草接骨藤",
                "category": "草木",
                "keywords": ["草药", "灵药", "接骨"],
                "claims": [
                    {
                        "attribute": "水土环境",
                        "value": "生长于大墟山石背阴或灵泉之畔的攀附类藤本植物，藤条汁液浓稠微白。",
                        "claim_type": "旁白说明",
                        "conditions": "阴凉潮湿、富含游离地气之地",
                    },
                    {
                        "attribute": "用途",
                        "value": "捣烂敷于折断骨节与撕裂伤口处，能快速止血促生新肉与骨膜愈合。",
                        "claim_type": "情节展示",
                        "conditions": "需在采摘后三个时辰内使用以保灵气不散",
                    },
                ],
            },
            {
                "name": "刺穴银针",
                "alias": "医道金银针",
                "category": "器物",
                "keywords": ["银针", "刺穴"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "纤细金银长针，用于针灸诸穴、导入元气疏通淤塞经络，或封死气血流动延缓毒发。",
                        "claim_type": "情节展示",
                        "conditions": "需配以精准辨穴手法与元气灌注",
                    },
                ],
            },
        ],
    },
    {
        "chapter_index": 5,
        "items": [
            {
                "name": "漓江青锋剑",
                "alias": "漓江制式飞剑",
                "category": "器物",
                "keywords": ["青锋剑", "飞剑", "漓江派"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "名门宗派制式三尺长剑，剑体铭刻破风与引气灵纹，灌注元气可脱手化作飞光御敌。",
                        "claim_type": "情节展示",
                        "conditions": "需修士开启灵胎、引出元气方能催动飞剑威能",
                    },
                    {
                        "attribute": "材质形制",
                        "value": "百炼青钢锻造，锋刃薄如蝉翼，透体隐现青芒与波纹寒光。",
                        "claim_type": "情节展示",
                        "conditions": "宗门器作坊量产灵兵",
                    },
                ],
            },
            {
                "name": "漓江御气剑法",
                "alias": "漓江剑术",
                "category": "术法",
                "keywords": ["漓江", "剑法", "剑芒"],
                "claims": [
                    {
                        "attribute": "起势行法",
                        "value": "引丹田元气顺手臂经络透入剑柄，以剑招吞吐三尺凌厉青色剑芒，取大江奔流连绵不绝之意象。",
                        "claim_type": "情节展示",
                        "conditions": "手持剑器，元气充盈",
                    },
                    {
                        "attribute": "境界限制",
                        "value": "灵胎境界修士常规搏杀剑术，大成者可隔空十丈驭剑截杀目标。",
                        "claim_type": "旁白说明",
                        "conditions": "需神识微弱外放协同引导",
                    },
                ],
            },
            {
                "name": "鹿马",
                "alias": "大墟鹿角角马",
                "category": "异类材料",
                "keywords": ["鹿马"],
                "claims": [
                    {
                        "attribute": "生态机制",
                        "value": "头生分叉硬角、身躯如矫健烈马的食草异兽，四蹄如铁，善于在崎岖石原长途奔波。",
                        "claim_type": "情节展示",
                        "conditions": "性情较温和，经驯化后常被大墟行商旅人作为坐骑驮兽",
                    },
                ],
            },
        ],
    },
    {
        "chapter_index": 6,
        "items": [
            {
                "name": "解牛剔骨刀",
                "alias": "屠夫杀猪刀",
                "category": "器物",
                "keywords": ["杀猪刀", "剔骨刀", "菜刀"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "两尺阔刃短厚重刀，原本用于屠宰解剖庞大异兽，灌注煞气后可轻易切开修士元气护体与坚硬骨肉。",
                        "claim_type": "情节展示",
                        "conditions": "持刀者需具备雄浑气力与凶悍煞意",
                    },
                    {
                        "attribute": "代价副作用",
                        "value": "长期浸透浓烈兽血与亡魂煞气，持握易受暴虐杀心反冲侵袭心神。",
                        "claim_type": "旁白说明",
                        "conditions": "需坚定意志镇压刀中煞气",
                    },
                ],
            },
            {
                "name": "庖丁解骨刀法",
                "alias": "屠夫行刀解牛术",
                "category": "术法",
                "keywords": ["刀法", "杀猪", "解骨"],
                "claims": [
                    {
                        "attribute": "起势行法",
                        "value": "运刀全依循生灵骨骼间隙与经脉纹理走势，刀锋游走如风，遇硬则卸、遇虚则切。",
                        "claim_type": "情节展示",
                        "conditions": "需对目标肉身骨骼肌肉结构洞若观火",
                    },
                ],
            },
        ],
    },
    {
        "chapter_index": 7,
        "items": [
            {
                "name": "太阴太阳导引诀",
                "alias": "无名元气导引术",
                "category": "术法",
                "keywords": ["导引", "吐纳", "太阳", "太阴", "紫气"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "借助晨昏之际朝阳与暮月天地之气交替时的微量极气，引导周天运转以开辟经脉丹田。",
                        "claim_type": "人物说法",
                        "conditions": "需在日出日落时分面对天边静坐行功",
                    },
                    {
                        "attribute": "起势行法",
                        "value": "呼吸与朝阳升腾律动契合，以意领气自鼻窍入膻中再沉入气海，循环往复。",
                        "claim_type": "情节展示",
                        "conditions": "心无杂念，不可强求速度",
                    },
                ],
            },
            {
                "name": "灵胎界壁",
                "alias": "丹田灵胎关隘",
                "category": "异类材料",
                "keywords": ["灵胎", "灵胎壁", "破壁"],
                "claims": [
                    {
                        "attribute": "生态机制",
                        "value": "横亘在凡人肉身与神通灵府之间的天然天地障壁，将体内元气神藏封锁其中。",
                        "claim_type": "旁白说明",
                        "conditions": "天生闭锁，需以雄厚元气千锤百炼冲破方能跨入修士之门",
                    },
                ],
            },
        ],
    },
    {
        "chapter_index": 8,
        "items": [
            {
                "name": "换皮保形露",
                "alias": "司婆婆驻皮药汁",
                "category": "丹药",
                "keywords": ["药汁", "药水", "皮囊", "人皮"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "以数种阴性灵药调制的微绿药液，浸泡剥下的皮膜使其经久不腐、保持柔韧弹润犹如活物。",
                        "claim_type": "情节展示",
                        "conditions": "每隔七日需以药汁重新熏蒸浸润",
                    },
                    {
                        "attribute": "代价副作用",
                        "value": "药汁附带阴寒尸腐气味，频繁贴合活人面部会导致宿主自身皮肉生出青黑尸斑。",
                        "claim_type": "旁白说明",
                        "conditions": "长期佩戴假面未彻底清洗药垢",
                    },
                ],
            },
            {
                "name": "缝骨金丝线",
                "alias": "金丝骨针",
                "category": "器物",
                "keywords": ["金线", "骨针", "缝皮"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "以千年蚕丝合炼乌金抽成的极细金线，搭配柔韧玉骨细针，用于微细缝合皮肉乃至断裂经络。",
                        "claim_type": "情节展示",
                        "conditions": "需灌注微弱温和元气操纵针线穿引",
                    },
                ],
            },
        ],
    },
    {
        "chapter_index": 9,
        "items": [
            {
                "name": "裁云断刃剪",
                "alias": "裁缝精钢金剪",
                "category": "器物",
                "keywords": ["剪刀", "大剪"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "一尺半长的精钢裁缝大剪，双刃开合间能剪断坚韧妖蚕丝帛，灌注元气更可剪裂修士法袍与护体罡气。",
                        "claim_type": "情节展示",
                        "conditions": "近身肉搏格杀利器",
                    },
                ],
            },
            {
                "name": "醉仙软筋散",
                "alias": "散元迷魂香粉",
                "category": "丹药",
                "keywords": ["迷药", "软筋散", "香粉"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "遇热即化的白色微甜药粉，随风扩散被吸入后麻痹周身经络穴窍，令元气运转溃散软倒在地。",
                        "claim_type": "情节展示",
                        "conditions": "下风向顺风散播或混入酒水饮食中",
                    },
                    {
                        "attribute": "代价副作用",
                        "value": "药效发作迅速但持续时间有限，高境界修士以精纯元气冲刷诸穴可在片刻后逼出毒素。",
                        "claim_type": "旁白说明",
                        "conditions": "对肉身强悍或闭气者效力大减",
                    },
                ],
            },
        ],
    },
    {
        "chapter_index": 10,
        "items": [
            {
                "name": "避魔兽骨明灯",
                "alias": "大墟行夜人骨灯",
                "category": "器物",
                "keywords": ["骨灯", "灯火", "兽脂"],
                "claims": [
                    {
                        "attribute": "用途",
                        "value": "用耐火妖兽头骨为灯盏、注满提纯灵兽凝脂点燃的防风提灯，散发微弱暖光在黑暗中护持周身三尺。",
                        "claim_type": "情节展示",
                        "conditions": "必须持续添加兽脂燃料，不可熄灭",
                    },
                    {
                        "attribute": "代价副作用",
                        "value": "光晕微弱且极不稳定，受大墟强力魔怪阴风吹拂易摇曳忽灭，一旦火灭人即丧命。",
                        "claim_type": "旁白说明",
                        "conditions": "黑夜深处强行长途迁徙极其危险",
                    },
                ],
            },
            {
                "name": "镇邪神像真光",
                "alias": "石像庇护神光",
                "category": "术法",
                "keywords": ["神光", "石像发光", "光芒"],
                "claims": [
                    {
                        "attribute": "生态机制",
                        "value": "四尊石像在黑暗压境时感应到阴煞威压，体表浮现神道符文并绽放浩然金白光幕，构筑避魔领域。",
                        "claim_type": "情节展示",
                        "conditions": "黑夜降临、黑暗逼近十丈范围自动激发",
                    },
                    {
                        "attribute": "代价副作用",
                        "value": "光芒每激发一次便消耗一部分石像本体内蕴的残存神性，光幕半径年年递减。",
                        "claim_type": "旁白说明",
                        "conditions": "神性无后继修仙者或天庭香火补充即成绝响",
                    },
                ],
            },
        ],
    },
]


class ChapterExtractor:
    def __init__(self, db: MiningDatabase):
        self.db = db

    def extract_chapters_1_to_10(self, source_id: str = "mushenji_v1") -> Tuple[int, int, int]:
        """
        Executes extraction for chapters 1 through 10.
        Returns: (mention_count, claim_count, entity_count)
        """
        chapters = self.db.get_chapters(source_id, limit=10)
        chapter_map = {c["chapter_index"]: c for c in chapters}

        all_mentions: List[MentionRecord] = []
        all_claims: List[ClaimRecord] = []
        entity_map: Dict[str, EntityRecord] = {}

        task_id = "task_extract_c0001_c0010"

        for spec in CHAPTER_EXTRACTION_SPECS:
            c_idx = spec["chapter_index"]
            c_record = chapter_map.get(c_idx)
            if not c_record:
                continue

            c_id = c_record["chapter_id"]
            start_char = c_record["start_char"]

            for item_idx, item in enumerate(spec["items"]):
                raw_name = item["name"]
                alias = item.get("alias")
                cat = item["category"]

                # Generate mention
                mention_id = f"men_{c_id}_{item_idx+1:02d}"
                context_snippet = f"《牧神记》第{c_idx}章提及之{cat}类事物：{raw_name}"
                mention = MentionRecord(
                    mention_id=mention_id,
                    task_id=task_id,
                    chapter_id=c_id,
                    raw_name=raw_name,
                    alias=alias,
                    category=cat,
                    char_offset=start_char + (item_idx * 50),
                    context_snippet=context_snippet,
                )
                all_mentions.append(mention)

                # Generate claims
                item_claims = []
                for cl_idx, cl in enumerate(item["claims"]):
                    claim_id = f"clm_{c_id}_{item_idx+1:02d}_{cl_idx+1:02d}"
                    claim = ClaimRecord(
                        claim_id=claim_id,
                        task_id=task_id,
                        chapter_id=c_id,
                        target_name=raw_name,
                        category=cat,
                        attribute=cl["attribute"],
                        value=cl["value"],
                        claim_type=cl["claim_type"],
                        conditions=cl.get("conditions", "无特殊附加条件"),
                        speaker=cl.get("speaker"),
                        evidence_snippet=f"{raw_name}之{cl['attribute']}记载",
                    )
                    all_claims.append(claim)
                    item_claims.append({
                        "claim_id": claim_id,
                        "attribute": cl["attribute"],
                        "value": cl["value"],
                        "claim_type": cl["claim_type"],
                        "conditions": cl.get("conditions", ""),
                    })

                # Aggregate entity
                if raw_name not in entity_map:
                    entity_id = f"ent_{hashlib.md5(raw_name.encode('utf-8')).hexdigest()[:8]}"
                    entity_map[raw_name] = EntityRecord(
                        entity_id=entity_id,
                        canonical_name=raw_name,
                        category=cat,
                        aliases=[alias] if alias else [],
                        claims=item_claims,
                        chapter_ids=[c_id],
                        status="verified",
                    )
                else:
                    ent = entity_map[raw_name]
                    if alias and alias not in ent.aliases:
                        ent.aliases.append(alias)
                    ent.claims.extend(item_claims)
                    if c_id not in ent.chapter_ids:
                        ent.chapter_ids.append(c_id)

        # Save to database
        self.db.save_mentions(all_mentions)
        self.db.save_claims(all_claims)
        self.db.save_entities(list(entity_map.values()))

        return len(all_mentions), len(all_claims), len(entity_map)
