"""Seeds test data for V3 Prompt Engine verification."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.tag import Tag
from models.character import Character
from models.lora import LoRA
from models.associations import CharacterTag

def seed_v3():
    session = SessionLocal()
    try:
        print("🌱 Seeding V3 Test Data...")
        
        # 1. Create/Update Essential Tags with Layers
        tags_data = [
            ("masterpiece", 0, "ANY", "High quality output", "명작"),
            ("best_quality", 0, "ANY", "Best quality details", "최고 화질"),
            ("1girl", 1, "PERMANENT", "One girl in the scene", "1소녀"),
            ("solo", 1, "PERMANENT", "Solo subject", "단독"),
            ("long_hair", 2, "PERMANENT", "Long hair style", "긴 머리"),
            ("blue_eyes", 2, "PERMANENT", "Blue colored eyes", "푸른 눈"),
            ("white_dress", 4, "TRANSIENT", "Wearing a white dress", "흰색 드레스"),
            ("sitting", 8, "TRANSIENT", "Sitting pose", "앉아있는"),
            ("classroom", 10, "ANY", "Inside a school classroom", "교실"),
            ("sunset", 11, "ANY", "Sunset lighting and atmosphere", "노을"),
            ("1boy", 1, "PERMANENT", "One boy in the scene", "1소년"),
            ("lowres", 0, "ANY", "Low resolution (negative)", "저화질"),
        ]
        
        for name, layer, scope, desc, ko in tags_data:
            tag = session.query(Tag).filter(Tag.name == name).first()
            if not tag:
                tag = Tag(name=name, default_layer=layer, usage_scope=scope, description=desc, ko_name=ko)
                session.add(tag)
            else:
                tag.default_layer = layer
                tag.usage_scope = scope
                tag.description = desc
                tag.ko_name = ko
        
        session.commit()
        print("   ✅ Tags created/updated")

        # 1.5 Create Test LoRA
        lora = session.query(LoRA).filter(LoRA.name == "dummy_lora").first()
        if not lora:
            lora = LoRA(
                name="dummy_lora",
                display_name="Dummy LoRA",
                lora_type="character",
                trigger_words=["dummy_trigger"]
            )
            session.add(lora)
            session.commit()
            print("   ✅ LoRA 'dummy_lora' created")

        # 2. Create Test Character: Hana
        hana = session.query(Character).filter(Character.name == "Hana").first()
        if not hana:
            hana = Character(
                name="Hana", 
                description="Test character for V3",
                gender="female",
                loras=[{"lora_id": lora.id, "weight": 0.8}]
            )
            session.add(hana)
            session.commit()
            print("   ✅ Character 'Hana' created")
        else:
            hana.loras = [{"lora_id": lora.id, "weight": 0.8}]
            session.commit()
        
        # 3. Associate Tags to Hana
        # Identity (Permanent)
        identity_tags = ["1girl", "solo", "long_hair", "blue_eyes"]
        for tag_name in identity_tags:
            tag = session.query(Tag).filter(Tag.name == tag_name).first()
            if tag:
                link = session.query(CharacterTag).filter(
                    CharacterTag.character_id == hana.id,
                    CharacterTag.tag_id == tag.id
                ).first()
                if not link:
                    link = CharacterTag(character_id=hana.id, tag_id=tag.id, is_permanent=True)
                    session.add(link)
        
        session.commit()
        print("   ✅ Hana tags associated")

        # 4. Create Basic Tag Rules
        from models.tag import TagRule

        # Ensure opposing tags exist
        opposing_tags = [
            ("1boy", 1, "PERMANENT"),
            ("lowres", 0, "ANY"),
        ]
        for name, layer, scope in opposing_tags:
            tag = session.query(Tag).filter(Tag.name == name).first()
            if not tag:
                tag = Tag(name=name, default_layer=layer, usage_scope=scope)
                session.add(tag)
        session.commit()

        # Rule 1: 1girl <-> 1boy Conflict
        t1 = session.query(Tag).filter(Tag.name == "1girl").first()
        t2 = session.query(Tag).filter(Tag.name == "1boy").first()
        if t1 and t2:
            existing_rule = session.query(TagRule).filter(
                TagRule.source_tag_id == t1.id, TagRule.target_tag_id == t2.id
            ).first()
            if not existing_rule:
                rule = TagRule(
                    rule_type="conflict",
                    source_tag_id=t1.id,
                    target_tag_id=t2.id,
                    message="Gender conflict detected"
                )
                session.add(rule)
                print("   ✅ Rule created: 1girl <-> 1boy")

        # Rule 2: masterpiece <-> lowres Conflict
        t3 = session.query(Tag).filter(Tag.name == "masterpiece").first()
        t4 = session.query(Tag).filter(Tag.name == "lowres").first()
        if t3 and t4:
            existing_rule = session.query(TagRule).filter(
                TagRule.source_tag_id == t3.id, TagRule.target_tag_id == t4.id
            ).first()
            if not existing_rule:
                rule = TagRule(
                    rule_type="conflict",
                    source_tag_id=t3.id,
                    target_tag_id=t4.id,
                    message="Quality conflict detected"
                )
                session.add(rule)
                print("   ✅ Rule created: masterpiece <-> lowres")

        session.commit()
        print("   ✅ Tag Rules seeded")

        print("\n✨ Seeding Complete!")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_v3()
