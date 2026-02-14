"""
Export Service Module
Handles exporting scraped data to various formats.
"""

import os
import json
import csv
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models.job import Job
from app.models.product import Product
from app.config import settings

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting scraped data."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the export service."""
        self.db = db
        self.export_path = settings.EXPORT_PATH
        
        # Ensure export directory exists
        os.makedirs(self.export_path, exist_ok=True)
    
    async def export_job_products(
        self,
        job_id: int,
        format: str = "csv",
        filename: Optional[str] = None
    ) -> str:
        """
        Export all products from a job.
        
        Args:
            job_id: Database job ID
            format: Export format (csv, excel, json)
            filename: Optional custom filename
        
        Returns:
            Path to exported file
        """
        # Get job
        job = await self.db.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Get products
        query = select(Product).where(Product.job_id == job_id)
        result = await self.db.execute(query)
        products = result.scalars().all()
        
        if not products:
            raise ValueError("No products to export")
        
        # Generate filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{job.domain}_{timestamp}"
        
        # Export based on format
        if format == "csv":
            return await self._export_csv(products, filename)
        elif format == "excel":
            return await self._export_excel(products, filename)
        elif format == "json":
            return await self._export_json(products, filename)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def _export_csv(
        self, 
        products: List[Product], 
        filename: str
    ) -> str:
        """Export products to CSV file."""
        filepath = os.path.join(self.export_path, f"{filename}.csv")
        
        # Define columns
        columns = [
            "Product ID", "SKU", "Name", "Description", "Price",
            "Original Price", "Currency", "In Stock", "Stock Quantity",
            "URL", "Image URL", "Category", "Subcategory", "Category Path",
            "Brand", "Manufacturer", "Rating", "Review Count",
            "Source", "Scraped At"
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            
            for product in products:
                row = {
                    "Product ID": product.product_id or "",
                    "SKU": product.sku or "",
                    "Name": product.name or "",
                    "Description": (product.description or "")[:500],
                    "Price": float(product.price) if product.price else "",
                    "Original Price": float(product.original_price) if product.original_price else "",
                    "Currency": product.currency or "GBP",
                    "In Stock": "Yes" if product.in_stock else "No",
                    "Stock Quantity": product.stock_quantity or "",
                    "URL": product.url or "",
                    "Image URL": product.image_url or "",
                    "Category": product.category or "",
                    "Subcategory": product.subcategory or "",
                    "Category Path": product.category_path or "",
                    "Brand": product.brand or "",
                    "Manufacturer": product.manufacturer or "",
                    "Rating": product.rating or "",
                    "Review Count": product.review_count or "",
                    "Source": product.source_domain or "",
                    "Scraped At": product.scraped_at.isoformat() if product.scraped_at else "",
                }
                writer.writerow(row)
        
        logger.info(f"Exported {len(products)} products to {filepath}")
        return filepath
    
    async def _export_excel(
        self, 
        products: List[Product], 
        filename: str
    ) -> str:
        """Export products to Excel file."""
        import pandas as pd
        
        filepath = os.path.join(self.export_path, f"{filename}.xlsx")
        
        # Convert to DataFrame
        data = []
        for product in products:
            data.append({
                "Product ID": product.product_id,
                "SKU": product.sku,
                "Name": product.name,
                "Description": product.description,
                "Price": float(product.price) if product.price else None,
                "Original Price": float(product.original_price) if product.original_price else None,
                "Currency": product.currency,
                "In Stock": product.in_stock,
                "Stock Quantity": product.stock_quantity,
                "URL": product.url,
                "Image URL": product.image_url,
                "Category": product.category,
                "Subcategory": product.subcategory,
                "Category Path": product.category_path,
                "Brand": product.brand,
                "Manufacturer": product.manufacturer,
                "Rating": product.rating,
                "Review Count": product.review_count,
                "Specifications": json.dumps(product.specifications) if product.specifications else "",
                "Source": product.source_domain,
                "Scraped At": product.scraped_at,
            })
        
        df = pd.DataFrame(data)
        
        # Write to Excel with formatting
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Products', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Products']
            for i, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                )
                worksheet.column_dimensions[chr(65 + i)].width = min(50, max_length + 2)
        
        logger.info(f"Exported {len(products)} products to {filepath}")
        return filepath
    
    async def _export_json(
        self, 
        products: List[Product], 
        filename: str
    ) -> str:
        """Export products to JSON file."""
        filepath = os.path.join(self.export_path, f"{filename}.json")
        
        data = {
            "export_date": datetime.now().isoformat(),
            "total_products": len(products),
            "products": []
        }
        
        for product in products:
            data["products"].append({
                "id": product.id,
                "product_id": product.product_id,
                "sku": product.sku,
                "name": product.name,
                "description": product.description,
                "price": float(product.price) if product.price else None,
                "original_price": float(product.original_price) if product.original_price else None,
                "currency": product.currency,
                "in_stock": product.in_stock,
                "stock_quantity": product.stock_quantity,
                "url": product.url,
                "image_url": product.image_url,
                "images": [img.url for img in product.images] if product.images else [],
                "category": product.category,
                "subcategory": product.subcategory,
                "category_path": product.category_path,
                "brand": product.brand,
                "manufacturer": product.manufacturer,
                "specifications": product.specifications,
                "features": product.features,
                "rating": product.rating,
                "review_count": product.review_count,
                "variants": [
                    {
                        "name": v.name,
                        "sku": v.sku,
                        "price": float(v.price) if v.price else None,
                        "in_stock": v.in_stock,
                        "attributes": v.attributes,
                    }
                    for v in product.variants
                ] if product.variants else [],
                "source_domain": product.source_domain,
                "scraped_at": product.scraped_at.isoformat() if product.scraped_at else None,
            })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(products)} products to {filepath}")
        return filepath
    
    async def export_filtered_products(
        self,
        format: str = "csv",
        domain: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        in_stock: Optional[bool] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Export filtered products across all jobs.
        
        Args:
            format: Export format
            domain: Filter by source domain
            category: Filter by category
            brand: Filter by brand
            min_price: Minimum price filter
            max_price: Maximum price filter
            in_stock: Filter by stock status
            filename: Optional custom filename
        
        Returns:
            Path to exported file
        """
        # Build query
        query = select(Product)
        
        if domain:
            query = query.where(Product.source_domain.ilike(f"%{domain}%"))
        if category:
            query = query.where(Product.category.ilike(f"%{category}%"))
        if brand:
            query = query.where(Product.brand.ilike(f"%{brand}%"))
        if min_price is not None:
            query = query.where(Product.price >= min_price)
        if max_price is not None:
            query = query.where(Product.price <= max_price)
        if in_stock is not None:
            query = query.where(Product.in_stock == in_stock)
        
        result = await self.db.execute(query)
        products = result.scalars().all()
        
        if not products:
            raise ValueError("No products match the filter criteria")
        
        # Generate filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"products_export_{timestamp}"
        
        # Export based on format
        if format == "csv":
            return await self._export_csv(products, filename)
        elif format == "excel":
            return await self._export_excel(products, filename)
        elif format == "json":
            return await self._export_json(products, filename)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def list_exports(self) -> List[Dict[str, Any]]:
        """List all export files."""
        exports = []
        
        for filename in os.listdir(self.export_path):
            filepath = os.path.join(self.export_path, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                exports.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "format": filename.split('.')[-1]
                })
        
        return sorted(exports, key=lambda x: x['created_at'], reverse=True)
    
    def delete_export(self, filename: str) -> bool:
        """Delete an export file."""
        filepath = os.path.join(self.export_path, filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Deleted export file: {filename}")
            return True
        
        return False