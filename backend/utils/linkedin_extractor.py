"""
LinkedIn Content Extractor

This module handles LinkedIn-specific content extraction including:
- Cookie authentication
- Profile content extraction
- Post content extraction
- LinkedIn-specific selectors and parsing
"""

import logging
from typing import Optional, List, Dict, Any
from playwright.async_api import Page
import urllib.parse

logger = logging.getLogger(__name__)

class LinkedInExtractor:
    """Handles LinkedIn-specific content extraction"""
    
    # LinkedIn-specific CSS selectors for different content types
    PROFILE_SELECTORS = [
        '.pv-text-details__left-panel',
        '.pv-top-card-profile-picture__container + div',
        '.text-heading-xlarge',
        '.text-body-medium',
        '.pv-shared-text-with-see-more',
        '.pv-about-section',
        '.pv-profile-section',
        '.pv-experience-section',
        '.pv-education-section',
        '.profile-section-card',
        '[data-field="experience_company"]',
        '[data-field="experience_title"]',
    ]
    
    POST_SELECTORS = [
        '.feed-shared-update-v2',
        '.share-update-card',
        '.feed-shared-text',
        '.feed-shared-article',
    ]
    
    @staticmethod
    def is_linkedin_url(url: str) -> bool:
        """Check if the URL is a LinkedIn URL"""
        return 'linkedin.com' in url.lower()
    
    @staticmethod
    async def set_linkedin_cookies(page: Page, cookies_string: str, url: str) -> bool:
        """
        Set LinkedIn authentication cookies
        
        Args:
            page: Playwright page instance
            cookies_string: Cookie string in format "name1=value1; name2=value2"
            url: The LinkedIn URL being accessed
            
        Returns:
            bool: True if cookies were set successfully
        """
        try:
            parsed_url = urllib.parse.urlparse(url)
            cookies_list = []
            
            for cookie_pair in cookies_string.split(';'):
                if '=' in cookie_pair:
                    name, value = cookie_pair.strip().split('=', 1)
                    cookies_list.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.linkedin.com',
                        'path': '/'
                    })
            
            # Set cookies in the browser context
            await page.context.add_cookies(cookies_list)
            logger.info(f"Set {len(cookies_list)} LinkedIn cookies for authentication")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to set LinkedIn cookies: {str(e)}")
            return False
    
    @staticmethod
    async def navigate_to_linkedin(page: Page, url: str) -> bool:
        """
        Navigate to LinkedIn URL with appropriate settings
        
        Args:
            page: Playwright page instance
            url: LinkedIn URL to navigate to
            
        Returns:
            bool: True if navigation was successful
        """
        try:
            # LinkedIn often blocks bots, use minimal wait
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            # Wait a bit for dynamic content to load
            await page.wait_for_timeout(3000)
            
            # Try to scroll down to load more content (for sites with lazy loading)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            
            # Wait for main content to appear (with fallback)
            try:
                await page.wait_for_selector("main, article, .content, #content", timeout=10000)
            except Exception:
                pass  # Continue if no main content selector found
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to LinkedIn URL: {str(e)}")
            return False
    
    @staticmethod
    async def extract_linkedin_content(page: Page) -> str:
        """
        Extract content from LinkedIn page using LinkedIn-specific selectors
        
        Args:
            page: Playwright page instance
            
        Returns:
            str: Extracted text content
        """
        try:
            # Try LinkedIn-specific extraction first
            article_text = await page.evaluate("""
                () => {
                    // Try different selectors for article content
                    const selectors = [
                        // LinkedIn-specific selectors
                        '.pv-text-details__left-panel',
                        '.pv-top-card-profile-picture__container + div',
                        '.text-heading-xlarge',
                        '.text-body-medium',
                        '.pv-shared-text-with-see-more',
                        '.pv-about-section',
                        '.pv-profile-section',
                        '.pv-experience-section',
                        '.pv-education-section',
                        '.feed-shared-update-v2',
                        '.share-update-card',
                        '.profile-section-card',
                        '[data-field="experience_company"]',
                        '[data-field="experience_title"]',
                    ];
                    
                    for (const selector of selectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            return element.innerText || element.textContent;
                        }
                    }
                    
                    // LinkedIn-specific comprehensive extraction
                    if (window.location.hostname.includes('linkedin.com')) {
                        let linkedinContent = [];
                        
                        // Get profile name and headline
                        const nameEl = document.querySelector('.text-heading-xlarge, .pv-text-details__left-panel h1');
                        if (nameEl) linkedinContent.push('Name: ' + nameEl.innerText.trim());
                        
                        const headlineEl = document.querySelector('.text-body-medium.break-words, .pv-text-details__left-panel .text-body-medium');
                        if (headlineEl) linkedinContent.push('Headline: ' + headlineEl.innerText.trim());
                        
                        // Get about section
                        const aboutEl = document.querySelector('.pv-about-section .pv-shared-text-with-see-more, .pv-about__summary-text');
                        if (aboutEl) linkedinContent.push('About: ' + aboutEl.innerText.trim());
                        
                        // Get experience
                        const experienceEls = document.querySelectorAll('.pv-experience-section .pv-entity__summary-info, .experience-item');
                        experienceEls.forEach((exp, i) => {
                            if (exp.innerText.trim()) {
                                linkedinContent.push(`Experience ${i+1}: ` + exp.innerText.trim());
                            }
                        });
                        
                        // Get education
                        const educationEls = document.querySelectorAll('.pv-education-section .pv-entity__summary-info, .education-item');
                        educationEls.forEach((edu, i) => {
                            if (edu.innerText.trim()) {
                                linkedinContent.push(`Education ${i+1}: ` + edu.innerText.trim());
                            }
                        });
                        
                        if (linkedinContent.length > 0) {
                            return linkedinContent.join('\\n\\n');
                        }
                    }
                    
                    // Fallback to body text
                    return document.body.innerText || document.body.textContent || '';
                }
            """)
            
            return article_text.strip() if article_text else ""
            
        except Exception as e:
            logger.warning(f"Failed to extract LinkedIn content: {str(e)}")
            return ""
    
    @staticmethod
    def get_linkedin_user_agent() -> str:
        """Get a realistic user agent for LinkedIn"""
        return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    @staticmethod
    def get_linkedin_timeout() -> int:
        """Get appropriate timeout for LinkedIn requests"""
        return 15000  # 15 seconds for LinkedIn (shorter due to anti-bot measures)
    
    @classmethod
    async def process_linkedin_url(
        cls, 
        page: Page, 
        url: str, 
        cookies: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Complete LinkedIn URL processing pipeline
        
        Args:
            page: Playwright page instance
            url: LinkedIn URL to process
            cookies: Optional cookies string for authentication
            
        Returns:
            tuple: (success: bool, extracted_text: str)
        """
        try:
            # Set LinkedIn-specific user agent
            await page.set_extra_http_headers({
                'User-Agent': cls.get_linkedin_user_agent()
            })
            
            # Set cookies if provided
            if cookies:
                success = await cls.set_linkedin_cookies(page, cookies, url)
                if not success:
                    logger.warning("Failed to set LinkedIn cookies, proceeding without authentication")
            
            # Navigate to LinkedIn URL
            if not await cls.navigate_to_linkedin(page, url):
                return False, ""
            
            # Extract content
            extracted_text = await cls.extract_linkedin_content(page)
            
            return True, extracted_text
            
        except Exception as e:
            logger.error(f"Failed to process LinkedIn URL: {str(e)}")
            return False, "" 