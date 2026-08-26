import asyncio
import os
import sys
import sqlite3
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.database import create_engine_with_config
from app.models.job import Job, JobStatus, JobType
from app.models.product import Product, ProductImage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from urllib.parse import urlparse

def get_sqlite():
    db_path = os.path.join(os.path.dirname(__file__), "..", "ecommerce_scraper.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

async def run_migration():
    conn = get_sqlite()
    cursor = conn.cursor()

    engine = create_engine_with_config()
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # 1. Migrate Jobs
        cursor.execute("SELECT * FROM jobs")
        job_rows = cursor.fetchall()
        print(f"Found {len(job_rows)} jobs in SQLite")
        
        job_map = {}
        for r in job_rows:
            rd = dict(r)
            try:
                existing = await db.execute(select(Job).where(Job.job_id == rd['job_id']))
                obj = existing.scalar_one_or_none()
                if not obj:
                    cfg = json.loads(rd['config']) if rd.get('config') and isinstance(rd['config'], str) else {}
                    st = json.loads(rd['stats']) if rd.get('stats') and isinstance(rd['stats'], str) else {}
                    
                    obj = Job(
                        job_id=rd['job_id'],
                        name=rd['name'] or "Job",
                        description=rd.get('description'),
                        url=rd['url'] or "http://example.com",
                        domain=rd.get('domain') or "example.com",
                        job_type=JobType.FULL_SITE,
                        status=JobStatus.COMPLETED if rd.get('status') == 'COMPLETED' else JobStatus.PENDING,
                        progress=float(rd.get('progress') or 0.0),
                        total_pages=rd.get('total_pages') or 0,
                        scraped_pages=rd.get('scraped_pages') or 0,
                        total_products=rd.get('total_products') or 0,
                        config=cfg,
                        stats=st,
                        error_message=rd.get('error_message')
                    )
                    db.add(obj)
                    await db.commit()
                job_map[rd['id']] = obj.id
            except Exception as e:
                await db.rollback()
                print(f"Skipping job {rd.get('job_id')}: {e}")

        print(f"Migrated {len(job_map)} Jobs to Neon DB")

        # 2. Migrate Products
        cursor.execute("SELECT * FROM products")
        prod_rows = cursor.fetchall()
        print(f"Found {len(prod_rows)} products in SQLite")

        prod_count = 0
        prod_map = {}
        for r in prod_rows:
            rd = dict(r)
            p_id = rd.get('product_id') or f"prod_{rd['id']}"
            try:
                existing = await db.execute(select(Product).where(Product.product_id == p_id))
                obj = existing.scalar_one_or_none()
                if not obj:
                    raw = json.loads(rd['raw_data']) if rd.get('raw_data') and isinstance(rd['raw_data'], str) else {}
                    cats = json.loads(rd['categories']) if rd.get('categories') and isinstance(rd['categories'], str) else []
                    
                    fk_job_id = job_map.get(rd.get('job_id'))
                    
                    url_val = rd.get('url') or "http://example.com"
                    domain_val = rd.get('source_domain') or rd.get('domain')
                    if not domain_val:
                        try: domain_val = urlparse(url_val).netloc
                        except Exception: domain_val = "example.com"

                    obj = Product(
                        product_id=p_id,
                        job_id=fk_job_id,
                        sku=rd.get('sku'),
                        upc=rd.get('upc'),
                        ean=rd.get('ean'),
                        name=rd.get('name') or rd.get('title') or "Scraped Product",
                        title=rd.get('title'),
                        description=rd.get('description'),
                        short_description=rd.get('short_description'),
                        price=float(rd.get('price')) if rd.get('price') is not None else None,
                        original_price=float(rd.get('original_price')) if rd.get('original_price') is not None else None,
                        sale_price=float(rd.get('sale_price')) if rd.get('sale_price') is not None else None,
                        currency=rd.get('currency') or "USD",
                        price_text=rd.get('price_text'),
                        discount_percentage=float(rd.get('discount_percentage')) if rd.get('discount_percentage') is not None else None,
                        in_stock=bool(rd.get('in_stock', True)),
                        stock_quantity=rd.get('stock_quantity'),
                        stock_status=rd.get('stock_status'),
                        url=url_val,
                        source_domain=domain_val,
                        image_url=rd.get('image_url'),
                        thumbnail_url=rd.get('thumbnail_url'),
                        category=rd.get('category'),
                        subcategory=rd.get('subcategory'),
                        category_path=rd.get('category_path'),
                        categories=cats,
                        brand=rd.get('brand'),
                        manufacturer=rd.get('manufacturer'),
                        vendor=rd.get('vendor'),
                        rating=float(rd.get('rating')) if rd.get('rating') is not None else None,
                        review_count=rd.get('review_count') or 0,
                        raw_data=raw
                    )
                    db.add(obj)
                    await db.commit()
                prod_map[rd['id']] = obj.id
                prod_count += 1
                if prod_count % 50 == 0:
                    print(f"Migrated {prod_count}/{len(prod_rows)} products...")
            except Exception as e:
                await db.rollback()
                print(f"Skipping product {p_id}: {e}")

        print(f"Successfully migrated {prod_count} Products to Neon DB")

        # 3. Migrate Product Images
        cursor.execute("SELECT * FROM product_images")
        img_rows = cursor.fetchall()
        print(f"Found {len(img_rows)} product images in SQLite")
        img_count = 0
        for r in img_rows:
            rd = dict(r)
            fk_prod_id = prod_map.get(rd.get('product_id'))
            if fk_prod_id:
                try:
                    img = ProductImage(
                        product_id=fk_prod_id,
                        url=rd.get('url') or "",
                        alt_text=rd.get('alt_text'),
                        is_primary=bool(rd.get('is_primary', False)),
                        display_order=rd.get('display_order') or 0
                    )
                    db.add(img)
                    await db.commit()
                    img_count += 1
                except Exception as e:
                    await db.rollback()
        print(f"Successfully migrated {img_count} Product Images to Neon DB")

    await engine.dispose()
    print("MIGRATION COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_migration())
