import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re

def fetch_product_data(tcin):
    url = f"https://www.target.com/p/-/A-{tcin}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
    except Exception as e:
        return {"tcin": tcin, "error": str(e)}

    soup = BeautifulSoup(res.text, "html.parser")

    # Look for JSON-LD structured data
    product_data = {}
    try:
        json_ld = soup.find("script", type="application/ld+json")
        if json_ld:
            data = json.loads(json_ld.string)
            product_data['title'] = data.get('name')
            offers = data.get('offers', {})
            product_data['regular_price'] = offers.get('price') if offers else None
            product_data['sale_price'] = offers.get('price') if offers else None  # Placeholder
            product_data['image_urls'] = data.get('image', [])[:3] if isinstance(data.get('image'), list) else [data.get('image')] if data.get('image') else []
    except Exception:
        pass

    # Alternative: parse embedded JS object for reviews and ratings
    try:
        script_text = soup.find_all("script", text=re.compile("window.__PRELOADED_STATE__"))[0].string
        json_text = re.search(r"window\.__PRELOADED_STATE__\s*=\s*({.*?});", script_text, re.DOTALL).group(1)
        data_json = json.loads(json_text)
        product_info = data_json.get('product', {})
        ratings = product_info.get('ratings', {})
        reviews = product_info.get('reviews', {})

        product_data['review_count'] = ratings.get('reviewsCount') or reviews.get('totalReviewCount')
        product_data['star_rating'] = ratings.get('averageRating') or reviews.get('averageRating')
    except Exception:
        # If unavailable, defaults
        product_data.setdefault('review_count', None)
        product_data.setdefault('star_rating', None)

    product_data['tcin'] = tcin
    return product_data

def main():
    st.title("Target PDP Scraper")

    tcin_input = st.text_area("Paste TCINs (one per line):")
    if not tcin_input.strip():
        st.info("Please enter TCINs to start scraping.")
        return

    tcins = list(set(t.strip() for t in tcin_input.strip().splitlines() if t.strip()))
    if st.button("Scrape Target Products"):
        results = []
        progress = st.progress(0)
        for idx, tcin in enumerate(tcins):
            data = fetch_product_data(tcin)
            results.append(data)
            progress.progress((idx + 1) / len(tcins))
        df = pd.DataFrame(results)
        st.dataframe(df)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "target_products.csv", "text/csv")

        try:
            excel = df.to_excel(index=False, engine='openpyxl')
            st.download_button("Download Excel", excel, "target_products.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception:
            st.warning("Install 'openpyxl' for Excel export.")

if __name__ == "__main__":
    main()
