import asyncio
import os
import sys
import sqlite3
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings
from app.models.database import Base, create_engine_with_config
from app.models.user import User
from app.models.job import Job, JobStatus, JobType
from app.models.product import Product, ProductImage, ProductVariant
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

def get_sqlite_conn():
    sqlite_path = os.path.join(os.path.dirname(__file__), "..", "ecommerce_scraper.db")
    if not os.path.exists(sqlite_path):
        print(f"SQLite DB file not found at {sqlite_path}")
        return None
    
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn

async def migrate():
    conn = get_sqlite_conn()
    if not conn:
        return

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t['name'] for t in cursor.fetchall() if t['name'] != 'sqlite_sequence']
    print(f"SQLite tables found: {tables}")

    engine = create_engine_with_config()
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("\nStarting clean migration to Neon PostgreSQL...")

    async with AsyncSessionLocal() as pg_session:

        # 1. Users
        if 'users' in tables:
            cursor.execute("SELECT * FROM users")
            user_count = 0
            for r in cursor.fetchall():
                rd = dict(r)
                try:
                    existing = await pg_session.execute(select(User).where(User.username == rd['username']))
                    if not existing.scalar_one_or_none():
                        u = User(
                            id=rd.get('id'),
                            email=rd.get('email'),
                            username=rd.get('username'),
                            full_name=rd.get('full_name'),
                            hashed_password=rd.get('hashed_password'),
                            is_active=bool(rd.get('is_active', True)),
                            is_superuser=bool(rd.get('is_superuser', False))
                        )
                        pg_session.add(u)
                        user_count += 1
                except Exception as e:
                    print(f"Error skipping user {rd.get('username')}: {e}")
            await pg_session.commit()
            print(f"Migrated {user_count} Users")

        # 2. Jobs
        if 'jobs' in tables:
            cursor.execute("SELECT * FROM jobs")
            job_count = 0
            for r in cursor.fetchall():
                rd = dict(r)
                try:
                    existing = await pg_session.execute(select(Job).where(Job.job_id == rd['job_id']))
                    if not existing.scalar_one_or_none():
                        cfg = rd.get('config')
                        if isinstance(cfg, str) and cfg:
                            try: cfg = json.loads(cfg)
                            except Exception: cfg = {}
                        elif not isinstance(cfg, dict): cfg = {}

                        st = rd.get('stats')
                        if isinstance(st, str) and st:
                            try: st = json.loads(st)
                            except Exception: st = {}
                        elif not isinstance(st, dict): st = {}

                        jt_raw = str(rd.get('job_type', 'full_site')).lower()
                        st_raw = str(rd.get('status', 'pending')).lower()

                        try: jt_val = JobType(jt_raw)
                        except ValueError: jt_val = JobType.FULL_SITE

                        try: st_val = JobStatus(st_raw)
                        except ValueError: st_val = JobStatus.PENDING

                        j = Job(
                            id=rd.get('id'),
                            job_id=rd.get('job_id'),
                            name=rd.get('name') or "Scrape Job",
                            description=rd.get('description'),
                            url=rd.get('url') or "http://example.com",
                            domain=rd.get('domain') or "example.com",
                            job_type=jt_val,
                            status=st_val,
                            progress=float(rd.get('progress') or 0.0),
                            total_pages=int(rd.get('total_pages') or 0),
                            scraped_pages=int(rd.get('scraped_pages') or 0),
                            total_products=int(rd.get('total_products') or 0),
                            failed_pages=int(rd.get('failed_pages') or 0),
                            config=cfg,
                            stats=st,
                            error_message=rd.get('error_message')
                        )
                        pg_session.add(j)
                        job_count += 1
                except Exception as e:
                    print(f"Error skipping job {rd.get('job_id')}: {e}")
            await pg_session.commit()
            print(f"Migrated {job_count} Jobs")

        # Fetch list of existing job IDs in Postgres
        existing_job_ids = set((await pg_session.execute(select(Job.id))).scalars().all())
        print(f"Valid Job IDs in Postgres: {existing_job_ids}")

        # 3. Products
        if 'products' in tables:
            cursor.execute("SELECT * FROM products")
            prod_count = 0
            for r in cursor.fetchall():
                rd = dict(r)
                try:
                    p_id = rd.get('product_id') or f"prod_{rd.get('id')}"
                    existing = await pg_session.execute(select(Product).where(Product.product_id == p_id))
                    if not existing.scalar_one_or_none():
                        raw = rd.get('raw_data')
                        if isinstance(raw, str) and raw:
                            try: raw = json.loads(raw)
                            except Exception: raw = {}
                        elif not isinstance(raw, dict): raw = {}

                        cats = rd.get('categories')
                        if isinstance(cats, str) and cats:
                            try: cats = json.loads(cats)
                            except Exception: cats = []
                        elif not isinstance(cats, list): cats = []

                        j_id = rd.get('job_id')
                        if j_id not in existing_job_ids:
                            j_id = None

                        p = Product(
                            id=rd.get('id'),
                            product_id=p_id,
                            job_id=j_id,
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
                            url=rd.get('url') or "http://example.com",
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
                            review_count=rd.get('review_count'),
                            raw_data=raw
                        )
                        pg_session.add(p)
                        prod_count += 1
                except Exception as e:
                    print(f"Error skipping product {rd.get('product_id')}: {e}")
            await pg_session.commit()
            print(f"Migrated {prod_count} Products")

        # Fetch list of existing product IDs in Postgres
        existing_prod_ids = set((await pg_session.execute(select(Product.id))).scalars().all())

        # 4. Product Images
        if 'product_images' in tables:
            cursor.execute("SELECT * FROM product_images")
            img_count = 0
            for r in cursor.fetchall():
                rd = dict(r)
                p_fk = rd.get('product_id')
                if p_fk not in existing_prod_ids:
                    continue
                try:
                    img = ProductImage(
                        id=rd.get('id'),
                        product_id=p_fk,
                        url=rd.get('url') or "",
                        alt_text=rd.get('alt_text'),
                        is_primary=bool(rd.get('is_primary', False)),
                        display_order=rd.get('display_order') or 0
                    )
                    pg_session.add(img)
                    img_count += 1
                except Exception as e:
                    print(f"Error skipping image: {e}")
            await pg_session.commit()
            print(f"Migrated {img_count} Product Images")

    await engine.dispose()
    print("\nALL DATA MIGRATED SUCCESSFULLY TO NEON POSTGRESQL!")

if __name__ == "__main__":
    asyncio.run(migrate())
