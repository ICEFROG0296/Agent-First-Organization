import json
from typing import Any, Dict
import logging

import shopify

# general GraphQL navigation utilities
from arklex.env.tools.shopify.utils_nav import *
from arklex.env.tools.shopify.utils import authorify

# ADMIN
from arklex.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from arklex.env.tools.tools import register_tool

logger = logging.getLogger(__name__)

description = "Get the inventory information and description details of a product."
slots = [
    ShopifySlots.PRODUCT_IDS,
    *PAGEINFO_SLOTS
]
outputs = [
    ShopifyOutputs.PRODUCTS_DETAILS,
    *PAGEINFO_OUTPUTS
]
PRODUCTS_NOT_FOUND = "error: product not found"
errors = [PRODUCTS_NOT_FOUND]

@register_tool(description, slots, outputs, lambda x: x not in errors)
def get_products(product_ids: list, **kwargs) -> str:
    nav = cursorify(kwargs)
    if not nav[1]:
        return nav[0]
    auth = authorify(kwargs)
    if auth["error"]:
        return auth["error"]

    try:
        ids = ' OR '.join(f'id:{pid.split("/")[-1]}' for pid in product_ids)
        with shopify.Session.temp(**auth["value"]):
            response = shopify.GraphQL().execute(f"""
                {{
                    products ({nav[0]}, query:"{ids}") {{
                        nodes {{
                            id
                            title
                            description
                            totalInventory
                            onlineStoreUrl
                            category {{
                                name
                            }}
                            images(first: 1) {{
                                edges {{
                                    node {{
                                        src
                                        altText
                                    }}
                                }}
                            }}
                            variants (first: 2) {{
                                nodes {{
                                    displayName
                                    id
                                    price
                                    inventoryQuantity
                                }}
                            }}
                        }}
                        pageInfo {{
                            endCursor
                            hasNextPage
                            hasPreviousPage
                            startCursor
                        }}
                    }}
                }}
            """)
            result = json.loads(response)['data']['products']
            response = result["nodes"]
            response_text = ""
            for i, product in enumerate(response):
                response_text += f"Product {i+1}:\n"
                response_text += f"Product Title: {product.get('title')}\n"
                response_text += f"Product Description: {product.get('description')}\n"
                response_text += f"Total Inventory: {product.get('totalInventory')}\n"
                response_text += f"Online Store URL: {product.get('onlineStoreUrl')}\n"
                images = product.get('images', {}).get('edges', [])
                if images:
                    default_image = images[0]['node']
                    response_text += f"Product Image URL: {default_image['src']}\n\n"
            return response_text
    except Exception as e:
        return PRODUCTS_NOT_FOUND
