"""
Generic Web Content Extractor

This module handles general web content extraction for non-LinkedIn sites including:
- Article content extraction
- Blog post extraction
- News content extraction
- Generic content selectors
"""

import logging
from typing import Optional
from playwright.async_api import Page

logger = logging.getLogger(__name__)

class WebExtractor:
    """Handles generic web content extraction"""
    
    # Generic content selectors for different types of websites
    CONTENT_SELECTORS = [
        'article',
        '[data-testid="storyContent"]',
        'main',
        '.content',
        '#content',
        '.post-content',
        '.entry-content',
        '.article-content',
        '.story-content',
        '.news-content',
        '.blog-content',
        '.page-content',
    ]
    
    @staticmethod
    def get_default_user_agent() -> str:
        """Get a realistic user agent for general web browsing"""
        return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    @staticmethod
    def get_default_timeout() -> int:
        """Get default timeout for general web requests"""
        return 60000  # 60 seconds for general websites
    
    @staticmethod
    async def navigate_to_url(page: Page, url: str) -> bool:
        """
        Navigate to a general URL with appropriate settings
        
        Args:
            page: Playwright page instance
            url: URL to navigate to
            
        Returns:
            bool: True if navigation was successful
        """
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait a bit for dynamic content to load
            await page.wait_for_timeout(3000)
            
            # Try to scroll down to load more content (for sites with lazy loading)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            
            # Wait for main content to appear (with fallback)
            try:
                await page.wait_for_selector("main, article, .content, #content, [data-testid='storyContent']", timeout=10000)
            except Exception:
                pass  # Continue if no main content selector found
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to URL: {str(e)}")
            return False
    
    @staticmethod
    async def extract_web_content(page: Page) -> str:
        """
        Extract content from a general web page using common selectors
        
        Args:
            page: Playwright page instance
            
        Returns:
            str: Extracted text content
        """
        try:
            article_text = await page.evaluate("""
                () => {
                    // Try different selectors for article content
                    const selectors = [
                        'article',
                        '[data-testid="storyContent"]',
                        'main',
                        '.content',
                        '#content',
                        '.post-content',
                        '.entry-content',
                        '.article-content',
                        '.story-content',
                        '.news-content',
                        '.blog-content',
                        '.page-content',
                    ];
                    
                    for (const selector of selectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            return element.innerText || element.textContent;
                        }
                    }
                    
                    // Fallback to body text
                    return document.body.innerText || document.body.textContent || '';
                }
            """)
            
            return article_text.strip() if article_text else ""
            
        except Exception as e:
            logger.warning(f"Failed to extract web content: {str(e)}")
            return ""
    
    @classmethod
    async def process_web_url(cls, page: Page, url: str) -> tuple[bool, str]:
        """
        Complete web URL processing pipeline
        
        Args:
            page: Playwright page instance
            url: URL to process
            
        Returns:
            tuple: (success: bool, extracted_text: str)
        """
        try:
            # Set general user agent
            await page.set_extra_http_headers({
                'User-Agent': cls.get_default_user_agent()
            })
            
            # Navigate to URL
            if not await cls.navigate_to_url(page, url):
                return False, ""
            
            # Extract content
            extracted_text = await cls.extract_web_content(page)
            
            return True, extracted_text
            
        except Exception as e:
            logger.error(f"Failed to process web URL: {str(e)}")
            return False, "" 