import re
import json
from urllib.parse import urlparse
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from crawler import CrawlResult, PageData

# ponytail: Helper functions to extract schema tags from BeautifulSoup
def get_schemas(soup: BeautifulSoup) -> List[str]:
    if not soup:
        return []
    schemas = soup.find_all("script", type="application/ld+json")
    types = []
    for s in schemas:
        try:
            data = json.loads(s.string or s.get_text() or "{}")
            def recurse_types(node):
                if isinstance(node, list):
                    for item in node:
                        recurse_types(item)
                elif isinstance(node, dict):
                    t = node.get("@type", "")
                    if t:
                        if isinstance(t, list):
                            types.extend(t)
                        else:
                            types.append(t)
                    # Recurse into graph or other attributes
                    if "@graph" in node:
                        recurse_types(node["@graph"])
                    for k, v in node.items():
                        if isinstance(v, (dict, list)):
                            recurse_types(v)
            recurse_types(data)
        except Exception:
            pass
    return types

def get_microdata_types(soup: BeautifulSoup) -> List[str]:
    if not soup:
        return []
    types = []
    for elem in soup.find_all(itemtype=True):
        it = elem.get("itemtype")
        if isinstance(it, str):
            t = it.split("/")[-1]
            types.append(t)
    return types

def classify_page_type(url: str, html: str, soup: Optional[BeautifulSoup] = None, overrides: Optional[dict] = None) -> str:
    """
    Classify page types (homepage, service, location, contact, about, blog_article,
    ecommerce_product, ecommerce_category, utility, policy, other).
    """
    if overrides:
        # Check exact and regex overrides
        for pattern, p_type in overrides.items():
            try:
                if re.search(pattern, url):
                    return p_type
            except Exception:
                pass
            if pattern in url:
                return p_type

    if not soup and html:
        soup = BeautifulSoup(html, "html.parser")

    parsed = urlparse(url)
    path = parsed.path.lower().rstrip("/")
    if not path or path in ("", "/index.html", "/index.php", "/home"):
        return "homepage"

    schemas = []
    if soup:
        schemas = get_schemas(soup) + get_microdata_types(soup)
    schemas_lower = [s.lower() for s in schemas]

    if "product" in schemas_lower or "individualproduct" in schemas_lower:
        return "ecommerce_product"
    if "aboutpage" in schemas_lower:
        return "about"
    if "contactpage" in schemas_lower:
        return "contact"
    if any(x in schemas_lower for x in ("blogposting", "article", "newsarticle", "techarticle")):
        return "blog_article"
    if any(x in schemas_lower for x in ("collectionpage", "itempage", "offercatalog")):
        return "ecommerce_category"

    # Path pattern matching
    if any(x in path for x in ("/login", "/logout", "/cart", "/checkout", "/search", "/admin", "/dashboard", "/signup", "/register", "/signin")):
        return "utility"
    if any(x in path for x in ("/privacy", "/terms", "/cookie", "/legal", "/disclaimer", "/tos", "/privacy-policy", "/terms-of-service")):
        return "policy"
    if any(x in path for x in ("/contact", "/contact-us", "/get-in-touch", "/reach-us", "/estimate", "/quote")):
        return "contact"
    if any(x in path for x in ("/about", "/about-us", "/our-team", "/team", "/staff", "/history", "/about-me")):
        return "about"
    if any(x in path for x in ("/locations", "/location/", "/store/", "/find-us", "/address", "/stores/")):
        return "location"
    if any(x in path for x in ("/product/", "/item/", "/p/")):
        return "ecommerce_product"
    if any(x in path for x in ("/category/", "/collection/", "/shop", "/c/")):
        return "ecommerce_category"
    if any(x in path for x in ("/blog/", "/article/", "/news/", "/posts/", "/post/")):
        return "blog_article"
    if any(x in path for x in ("/services", "/service/", "/work", "/portfolio", "/features", "/solutions")):
        return "service"

    # DOM content heuristic
    if soup:
        forms = soup.find_all("form")
        for form in forms:
            action = form.get("action", "").lower()
            inputs = form.find_all(["input", "textarea", "select"])
            input_attrs = ""
            for inp in inputs:
                input_attrs += " " + str(inp.get("name", "")).lower() + " " + str(inp.get("placeholder", "")).lower() + " " + str(inp.get("id", "")).lower()
            form_text = form.get_text().lower() + input_attrs
            if "contact" in action or any(x in form_text for x in ("message", "email", "phone", "subject", "telephone", "comment")):
                if not ("search" in action or "newsletter" in form_text or "subscribe" in form_text):
                    if any(x in path for x in ("contact", "write", "message", "support")):
                        return "contact"

    return "other"

def classify_site_type(crawl_result: CrawlResult, overrides: Optional[dict] = None) -> str:
    """
    Classify site intent based on crawl characteristics.
    Returns: local_service_business, local_storefront, multi_location_business,
             national_saas, ecommerce, publisher, corporate, other.
    """
    if overrides and "site_type" in overrides:
        return overrides["site_type"]

    has_map_embed = False
    has_local_phone = False
    has_address = False
    product_schemas_count = 0
    local_business_schemas_count = 0
    article_schemas_count = 0
    blog_count = 0
    product_url_count = 0
    service_url_count = 0
    location_url_count = 0

    # US-centric local phone patterns and local structures
    phone_pattern = re.compile(r'\b(?:\+?1[-.●]?)?\(?([2-9][0-8][0-9])\)?[-.●]?([2-9][0-9]{2})[-.●]?([0-9]{4})\b')
    address_pattern = re.compile(r'\b\d+\s+[A-Za-z0-9\.\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir|Pkwy|Parkway)\b', re.IGNORECASE)

    has_local_signals = False
    for url, page in crawl_result.pages.items():
        parsed = urlparse(url)
        path = parsed.path.lower()
        if "product" in path or "/p/" in path:
            product_url_count += 1
        if "service" in path or "/services" in path:
            service_url_count += 1
        if "location" in path or "store" in path:
            location_url_count += 1
        if "blog" in path or "article" in path or "news" in path:
            blog_count += 1

        if not page.soup:
            continue

        page_schemas = get_schemas(page.soup) + get_microdata_types(page.soup)
        for s in page_schemas:
            s_lower = s.lower()
            if "localbusiness" in s_lower or any(x in s_lower for x in ("store", "restaurant", "dentist", "plumber", "automotivebusiness")):
                local_business_schemas_count += 1
            if "product" in s_lower:
                product_schemas_count += 1
            if any(x in s_lower for x in ("article", "blogposting")):
                article_schemas_count += 1

        if page.soup.find("iframe", src=re.compile(r'google\.com/maps|maps\.google\.com')):
            has_map_embed = True

        body_text = page.soup.get_text()
        if phone_pattern.search(body_text):
            has_local_phone = True
        if address_pattern.search(body_text):
            has_address = True
        if any(x in body_text.lower() for x in ("serving", "service area", "service-area", "plumber", "plumbing", "dentist", "hvac", "roofing", "electrician")):
            has_local_signals = True

    # Rule checks in priority order
    if location_url_count >= 2:
        return "multi_location_business"
    if product_schemas_count >= 2 or product_url_count >= 2:
        return "ecommerce"
    if article_schemas_count >= 3 or blog_count >= 3:
        return "publisher"
    if local_business_schemas_count > 0 or has_map_embed or (has_local_phone and (has_address or has_local_signals)):
        if has_map_embed or has_address:
            return "local_storefront"
        else:
            return "local_service_business"

    homepage = crawl_result.homepage
    if homepage and homepage.soup:
        title_text = homepage.soup.find("title").get_text().lower() if homepage.soup.find("title") else ""
        h1_text = " ".join([h.get_text().lower() for h in homepage.soup.find_all("h1")])
        if any(x in (title_text + h1_text) for x in ("saas", "platform", "software", "cloud api", "developer tool", "enterprise solution", "subscription")):
            if not has_map_embed and local_business_schemas_count == 0:
                return "national_saas"

    if service_url_count >= 1:
        return "corporate"

    return "other"

def classify_location_model(site_type: str, crawl_result: CrawlResult, overrides: Optional[dict] = None) -> str:
    """
    Categorize the local operations model (storefront, service_area, multi_location, national_no_local).
    """
    if overrides and "location_model" in overrides:
        return overrides["location_model"]

    if site_type in ("national_saas", "ecommerce", "publisher", "corporate"):
        return "national_no_local"

    has_address = False
    has_map_embed = False
    location_url_count = 0

    address_pattern = re.compile(r'\b\d+\s+[A-Za-z0-9\.\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir|Pkwy|Parkway)\b', re.IGNORECASE)

    for url, page in crawl_result.pages.items():
        parsed = urlparse(url)
        path = parsed.path.lower()
        if "location" in path or "store" in path:
            location_url_count += 1

        if not page.soup:
            continue

        body_text = page.soup.get_text()
        if address_pattern.search(body_text):
            has_address = True
        if page.soup.find("iframe", src=re.compile(r'google\.com/maps|maps\.google\.com')):
            has_map_embed = True

    if site_type == "multi_location_business" or location_url_count >= 2:
        return "multi_location"
    if has_address or has_map_embed:
        return "storefront"
    if site_type in ("local_service_business", "local_storefront", "other"):
        return "service_area"

    return "national_no_local"
