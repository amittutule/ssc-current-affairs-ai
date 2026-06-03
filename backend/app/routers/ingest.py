from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict
from app.services.scraper import fetch_latest_news
from app.services.ai_service import summarize_article_for_ssc, get_embedding
from app.services.vector_db import upsert_summary
from app.services.pdf_generator import generate_daily_pdf

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])

def process_news_pipeline():
    """
    Background task to fetch news, summarize it, and save to Vector DB.
    """
    print("Starting news ingestion pipeline...")
    articles = fetch_latest_news(max_articles=5)
    print(f"Fetched {len(articles)} articles.")
    
    success_count = 0
    pdf_articles = []
    
    for idx, article in enumerate(articles):
        # 1. Summarize
        print(f"Summarizing article {idx + 1}: {article['title']}")
        summary = summarize_article_for_ssc(article['title'], article['content'])
        
        if "Could not generate" in summary:
            continue
            
        pdf_articles.append({"title": article['title'], "summary": summary})
            
        # 2. Embed
        print(f"Generating embedding for article {idx + 1}...")
        embedding = get_embedding(summary)
        
        # 3. Store
        print(f"Upserting to Pinecone for article {idx + 1}...")
        upsert_summary(
            url=article['url'],
            title=article['title'],
            summary=summary,
            embedding=embedding
        )
        success_count += 1
        
    print("Generating Daily PDF...")
    generate_daily_pdf(pdf_articles)
        
    print(f"Pipeline finished. Successfully processed {success_count} articles.")

@router.post("/trigger")
def trigger_ingestion(background_tasks: BackgroundTasks):
    """
    Endpoint to manually trigger the daily news scraping and summation.
    """
    try:
        background_tasks.add_task(process_news_pipeline)
        return {"message": "News ingestion pipeline triggered in the background!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
