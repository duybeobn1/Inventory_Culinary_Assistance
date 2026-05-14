import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# Khoi tao Neo4j Driver
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

SOURCE_FILE = "global_terroir_hierarchical.json"

def migrate_to_neo4j():
    if not os.path.exists(SOURCE_FILE):
        print("Khong tim thay file JSON.")
        return

    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        master_db = json.load(f)

    with driver.session() as session:
        for country, regions in master_db.items():
            print(f"Dang xu ly quoc gia: {country}")
            
            # Tao node Country
            session.run("MERGE (c:Country {name: $name})", name=country)

            for region, seasons in regions.items():
                # Tao node Region va ket noi voi Country
                session.run("""
                    MATCH (c:Country {name: $country_name})
                    MERGE (r:Region {name: $region_name})
                    MERGE (c)-[:HAS_REGION]->(r)
                """, country_name=country, region_name=region)

                for season_name, ingredients in seasons.items():
                    # Tao node Season
                    session.run("MERGE (s:Season {name: $name})", name=season_name)

                    for ing in ingredients:
                        # Tao node Variety va ket noi voi Region, Season, Ingredient
                        session.run("""
                            MATCH (r:Region {name: $region_name})
                            MATCH (s:Season {name: $season_name})
                            
                            MERGE (v:Variety {
                                name: $variety_name,
                                base_name: $base_name
                            })
                            ON CREATE SET v.terroir_notes = $notes, v.peak_months = $months
                            
                            MERGE (r)-[:PRODUCES]->(v)
                            MERGE (v)-[:IN_SEASON]->(s)
                            
                            // Ket noi voi Ingredient goc (da co san trong graph cua ban)
                            MERGE (i:Ingredient {name: $base_name})
                            MERGE (v)-[:IS_A]->(i)
                        """, 
                        region_name=region, 
                        season_name=season_name,
                        variety_name=ing.get("specific_variety") or ing.get("produce_name"),
                        base_name=ing.get("produce_name"),
                        notes=ing.get("terroir_notes"),
                        months=ing.get("peak_months")
                        )

    print("Hoan tat xay dung do thi tri thuc Terroir tren Neo4j!")

if __name__ == "__main__":
    migrate_to_neo4j()
    driver.close()
#. import json
# import os
# from supabase import create_client, Client
# from dotenv import load_dotenv

# load_dotenv()

# # Khởi tạo Supabase Client
# url: str = os.getenv("SUPABASE_URL")
# key: str = os.getenv("SUPABASE_KEY")
# supabase: Client = create_client(url, key)

# SOURCE_FILE = "global_terroir_hierarchical.json"

# def migrate():
#     if not os.path.exists(SOURCE_FILE):
#         print(f"Lỗi: Không tìm thấy file {SOURCE_FILE}")
#         return

#     with open(SOURCE_FILE, "r", encoding="utf-8") as f:
#         master_db = json.load(f)

#     to_insert = []
    
#     print("Đang xử lý và làm phẳng dữ liệu...")

#     for country, regions in master_db.items():
#         for region, seasons in regions.items():
#             for season_name, ingredients in seasons.items():
#                 for ing in ingredients:
#                     # Chuẩn bị row để insert
#                     row = {
#                         "base_name": ing.get("produce_name"),
#                         "specific_variety": ing.get("specific_variety"),
#                         "season_name": season_name,
#                         "peak_months": ing.get("peak_months"),
#                         "region": region,
#                         "country": country,
#                         "terroir_notes": ing.get("terroir_notes")
#                     }
#                     to_insert.append(row)

#     print(f"Tổng cộng có {len(to_insert)} bản ghi cần di trú.")

#     # Insert theo batch (mỗi lần 100 bản ghi) để tránh quá tải API
#     batch_size = 100
#     for i in range(0, len(to_insert), batch_size):
#         batch = to_insert[i:i + batch_size]
#         try:
#             res = supabase.table("terroir_produce").upsert(batch).execute()
#             print(f"Đã hoàn thành: {min(i + batch_size, len(to_insert))}/{len(to_insert)}")
#         except Exception as e:
#             print(f"Lỗi tại batch {i}: {e}")

#     print("Hoàn tất di trú dữ liệu lên Supabase!")

# if __name__ == "__main__":
#     migrate()


