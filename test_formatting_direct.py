"""Direct test of formatting functions without LLM"""
# Define the formatting functions directly to avoid import issues
from typing import Any

def _format_product_table(products: list[dict[str, Any]], heading: str) -> str:
    if not products:
        return f"{heading}\nNo matching products found."
    
    lines = [heading, ""]
    lines.append("| Name | Category | Price | Quantity | Brand | Supplier |")
    lines.append("|------|----------|-------|----------|-------|----------|")
    
    preview_limit = 15
    for product in products[:preview_limit]:
        lines.append(
            f"| {product['name']} | {product['category']} | ${product['price']:.2f} | {product['quantity']} | {product['brand']} | {product['supplier']} |"
        )
    
    if len(products) > preview_limit:
        lines.append(f"\n*...and {len(products) - preview_limit} more product(s).*")
    
    return "\n".join(lines)


def _format_product_comparison(products: list[dict[str, Any]]) -> str:
    if len(products) < 2:
        return "Comparison requires at least 2 products."
    
    lines = ["Product Comparison", ""]
    
    # Create comparison table
    lines.append("| Attribute | " + " | ".join([f"Product {i+1}" for i in range(len(products))]) + " |")
    lines.append("|-----------|" + "|".join(["-----------" for _ in range(len(products))]) + "|")
    
    attributes = ["name", "category", "price", "quantity", "brand", "supplier"]
    attribute_labels = ["Name", "Category", "Price", "Quantity", "Brand", "Supplier"]
    
    for attr, label in zip(attributes, attribute_labels):
        row_values = []
        for product in products:
            if attr == "price":
                row_values.append(f"${product[attr]:.2f}")
            else:
                row_values.append(str(product[attr]))
        lines.append(f"| {label} | " + " | ".join(row_values) + " |")
    
    return "\n".join(lines)


def _format_summary(products: list[dict[str, Any]], heading: str) -> str:
    if not products:
        return f"{heading}\nNo products found."
    
    total_products = len(products)
    total_quantity = sum(p["quantity"] for p in products)
    total_value = sum(p["price"] * p["quantity"] for p in products)
    categories = set(p["category"] for p in products)
    avg_price = sum(p["price"] for p in products) / total_products if products else 0
    
    lines = [heading, ""]
    lines.append(f"**Summary:** {total_products} products across {len(categories)} categories")
    lines.append(f"**Total Stock:** {total_quantity} units")
    lines.append(f"**Total Value:** ${total_value:,.2f}")
    lines.append(f"**Average Price:** ${avg_price:.2f}")
    lines.append(f"**Categories:** {', '.join(sorted(categories))}")
    
    return "\n".join(lines)


def _format_product_list(products: list[dict[str, Any]], heading: str) -> str:
    if not products:
        return f"{heading}\n- No matching products found."

    preview_limit = 12
    lines = [heading]
    for product in products[:preview_limit]:
        lines.append(
            f"- {product['name']} | {product['category']} | qty {product['quantity']} | ${product['price']:.2f}"
        )
    if len(products) > preview_limit:
        lines.append(f"- ...and {len(products) - preview_limit} more product(s).")
    return "\n".join(lines)

# Sample product data for testing
sample_products = [
    {
        "name": "Laptop Pro 15",
        "category": "Electronics",
        "price": 1299.99,
        "quantity": 45,
        "brand": "TechCorp",
        "supplier": "TechCorp",
        "warehouse_location": "Main Warehouse",
        "description": "High-performance laptop"
    },
    {
        "name": "Wireless Mouse",
        "category": "Electronics",
        "price": 29.99,
        "quantity": 150,
        "brand": "TechCorp",
        "supplier": "TechCorp",
        "warehouse_location": "Main Warehouse",
        "description": "Ergonomic wireless mouse"
    },
    {
        "name": "Office Chair",
        "category": "Furniture",
        "price": 249.99,
        "quantity": 30,
        "brand": "ComfortSeating",
        "supplier": "ComfortSeating",
        "warehouse_location": "Main Warehouse",
        "description": "Ergonomic office chair"
    }
]

def test_table_format():
    print("="*60)
    print("TABLE FORMAT TEST")
    print("="*60)
    result = _format_product_table(sample_products, "Inventory Products")
    print(result)
    print()

def test_comparison_format():
    print("="*60)
    print("COMPARISON FORMAT TEST")
    print("="*60)
    result = _format_product_comparison(sample_products[:2])
    print(result)
    print()

def test_summary_format():
    print("="*60)
    print("SUMMARY FORMAT TEST")
    print("="*60)
    result = _format_summary(sample_products, "Inventory Summary")
    print(result)
    print()

def test_list_format():
    print("="*60)
    print("LIST FORMAT TEST (Default)")
    print("="*60)
    result = _format_product_list(sample_products, "Inventory Products")
    print(result)
    print()

if __name__ == "__main__":
    test_table_format()
    test_comparison_format()
    test_summary_format()
    test_list_format()
    
    print("="*60)
    print("All formatting tests completed successfully!")
    print("="*60)
