import streamlit as st
import requests
import pandas as pd
from io import BytesIO

def fetch_redsky_data(tcins):
    key = "ebf8e6183f6a4b9db2b7a39f8eeb65e5"
    url = "https://redsky.target.com/redsky_aggregations/v1/web/product_summary_with_fulfillment_v1"
    params = {
        "key": key,
        "tcins": ",".join(tcins),
        "store_id": "3230",
        "zip": "36100",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"API request failed: {e}")
        return []

    results = []
    products = data.get("data", {}).get("product", {})
    for tcin in tcins:
        product = products.get(tcin)
        if not product:
            results.append({"tcin": tcin, "error": "No data for this TCIN"})
            continue

        item = product.get("item", {})
        description = item.get("product_description", {})
        price = product.get("price", {})
        ratings = product.get("ratings_and_reviews", {})
        enrichment = item.get("enrichment", {})
        images_obj = enrichment.get("images", {})

        # Get up to 3 images from primary and alternative images
        image_urls = []
        primary = images_obj.get("primary_image_url")
        if primary:
            image_urls.append(primary)
        alternatives = images_obj.get("alternative_images", [])
        for img in alternatives:
            if len(image_urls) >= 3:
                break
            image_urls.append(img.get("image_url"))
        
        results.append({
            "tcin": tcin,
            "title": description.get("title"),
            "brand": item.get("brand"),
            "regular_retail": price.get("historical_retail"),
            "sale_retail": price.get("current_retail"),
            "review_count": ratings.get("count"),
            "star_rating": ratings.get("rating"),
            "image_1": image_urls[0] if len(image_urls) > 0 else None,
            "image_2": image_urls[1] if len(image_urls) > 1 else None,
            "image_3": image_urls[2] if len(image_urls) > 2 else None,
        })
    return results

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Target_Products')
    processed_data = output.getvalue()
    return processed_data

def main():
    st.title("Target.com TCIN Product Data Scraper - Redsky API")

    tcins_input = st.text_area("Paste TCINs (one per line):")
    export_format = st.radio("Choose export format:", ("CSV", "Excel"))

    if st.button("Fetch Product Data"):
        tcins = [t.strip() for t in tcins_input.splitlines() if t.strip()]
        if not tcins:
            st.warning("Please enter at least one TCIN.")
            return

        with st.spinner("Fetching data from Redsky API..."):
            results = fetch_redsky_data(tcins)
            if not results:
                st.error("No data returned.")
                return

            df = pd.DataFrame(results)
            st.dataframe(df)

            if export_format == "CSV":
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, "target_product_data.csv", "text/csv")
            else:
                excel_data = to_excel(df)
                st.download_button("Download Excel", excel_data, "target_product_data.xlsx", 
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    main()
