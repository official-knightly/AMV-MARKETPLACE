"""
AI Manager - Integrates Claude and OpenAI for intelligent marketplace features
"""
import os
import json
import base64
from typing import Dict, List, Optional
import anthropic
import openai
from PIL import Image
import io
from types import SimpleNamespace

class _NvidiaMessageAdapter:
    """Small Anthropic-shaped adapter so existing AI features can use NVIDIA NIM."""
    def __init__(self, client, model):
        self.client = client
        self.model = model

    def create(self, model=None, max_tokens=1024, messages=None, **kwargs):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages or [],
            max_tokens=max_tokens,
            temperature=kwargs.get("temperature", 0.2),
            stream=False,
        )
        content = completion.choices[0].message.content or ""
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.lstrip().startswith("json"):
                content = content.lstrip()[4:].strip()
        return SimpleNamespace(content=[SimpleNamespace(text=content)])


class _NvidiaClientAdapter:
    def __init__(self, client, model):
        self.messages = _NvidiaMessageAdapter(client, model)


class AIManager:
    def __init__(self):
        # Prefer the configured Claude provider; otherwise use the requested NVIDIA NIM API.
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        nvidia_key = os.environ.get("NVIDIA_API_KEY", "").strip()
        nvidia_model = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b").strip()
        self.provider = "anthropic" if anthropic_key else ("nvidia" if nvidia_key else "fallback")
        if anthropic_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
        elif nvidia_key:
            nvidia_client = openai.OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=nvidia_key,
            )
            self.anthropic_client = _NvidiaClientAdapter(nvidia_client, nvidia_model)
        else:
            self.anthropic_client = None
        openai.api_key = os.environ.get("OPENAI_API_KEY", "")

    def status(self):
        return {"configured": self.anthropic_client is not None, "provider": self.provider}
        
    # ==================== CONTENT MODERATION ====================
    
    def moderate_content(self, text: str, image_data: Optional[bytes] = None) -> Dict:
        """
        Use Claude to moderate gig descriptions, reviews, and content
        """
        try:
            prompt = f"""Analyze this content for a video editing marketplace and determine if it's appropriate.

Content: {text}

Check for:
1. Inappropriate language or hate speech
2. Scam indicators or misleading claims
3. Copyright infringement mentions
4. Spam or promotional content
5. Quality and professionalism

Respond in JSON format:
{{
    "is_appropriate": true/false,
    "confidence": 0.0-1.0,
    "issues": ["list of issues found"],
    "suggestions": ["improvement suggestions"],
    "category": "safe/warning/blocked"
}}"""

            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(message.content[0].text)
            return result
            
        except Exception as e:
            print(f"AI moderation error: {e}")
            return {
                "is_appropriate": True,
                "confidence": 0.5,
                "issues": [],
                "suggestions": [],
                "category": "safe"
            }
    
    # ==================== SMART GIG OPTIMIZATION ====================
    
    def optimize_gig_description(self, title: str, description: str, category: str) -> Dict:
        """
        Use Claude to improve gig titles and descriptions for better visibility
        """
        try:
            prompt = f"""You are an expert marketplace copywriter. Optimize this video editing gig for maximum appeal and conversions.

Title: {title}
Description: {description}
Category: {category}

Provide:
1. Improved title (max 80 chars, compelling, SEO-friendly)
2. Enhanced description (clear, professional, highlights value)
3. Suggested tags (5-10 relevant keywords)
4. Pricing recommendation (based on market standards)

Respond in JSON format:
{{
    "optimized_title": "...",
    "optimized_description": "...",
    "suggested_tags": ["tag1", "tag2", ...],
    "pricing_suggestion": {{
        "min": 100,
        "recommended": 250,
        "max": 500,
        "reasoning": "..."
    }},
    "improvements": ["what was improved"]
}}"""

            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(message.content[0].text)
            return result
            
        except Exception as e:
            print(f"AI optimization error: {e}")
            return {
                "optimized_title": title,
                "optimized_description": description,
                "suggested_tags": [],
                "pricing_suggestion": {"min": 100, "recommended": 200, "max": 500},
                "improvements": []
            }
    
    # ==================== INTELLIGENT SEARCH ====================
    
    def semantic_search(self, query: str, gigs: List[Dict]) -> List[Dict]:
        """
        Use AI to understand search intent and rank gigs semantically
        """
        try:
            gigs_text = "\n\n".join([
                f"ID: {g['id']}\nTitle: {g['title']}\nDescription: {g['description']}\nCategory: {g['category']}"
                for g in gigs[:20]  # Limit to avoid token limits
            ])
            
            prompt = f"""User is searching for: "{query}"

Available gigs:
{gigs_text}

Rank these gigs by relevance to the user's search intent. Consider:
- Semantic meaning (not just keyword matching)
- User intent (what they're really looking for)
- Quality indicators in descriptions

Respond with JSON array of gig IDs in order of relevance:
{{"ranked_ids": [1, 5, 3, ...]}}"""

            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(message.content[0].text)
            ranked_ids = result.get("ranked_ids", [])
            
            # Reorder gigs based on AI ranking
            gig_map = {g['id']: g for g in gigs}
            ranked_gigs = [gig_map[gid] for gid in ranked_ids if gid in gig_map]
            
            # Add remaining gigs
            remaining = [g for g in gigs if g['id'] not in ranked_ids]
            return ranked_gigs + remaining
            
        except Exception as e:
            print(f"AI search error: {e}")
            return gigs
    
    # ==================== AUTOMATED REVIEW ANALYSIS ====================
    
    def analyze_review(self, review_text: str, rating: float) -> Dict:
        """
        Use Claude to analyze review sentiment and extract insights
        """
        try:
            prompt = f"""Analyze this marketplace review:

Rating: {rating}/5
Review: {review_text}

Provide:
1. Sentiment analysis (positive/negative/neutral)
2. Key points mentioned
3. Actionable feedback for the seller
4. Red flags (if any)

Respond in JSON:
{{
    "sentiment": "positive/negative/neutral",
    "sentiment_score": 0.0-1.0,
    "key_points": ["point1", "point2"],
    "seller_feedback": "...",
    "red_flags": ["flag1", ...],
    "is_genuine": true/false
}}"""

            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(message.content[0].text)
            return result
            
        except Exception as e:
            print(f"AI review analysis error: {e}")
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.5,
                "key_points": [],
                "seller_feedback": "",
                "red_flags": [],
                "is_genuine": True
            }
    
    # ==================== SMART PRICING RECOMMENDATIONS ====================
    
    def recommend_pricing(self, gig_data: Dict, market_data: List[Dict]) -> Dict:
        """
        Use AI to analyze market and recommend optimal pricing
        """
        try:
            market_summary = "\n".join([
                f"- {g['title']}: ₹{g['price']} (rating: {g['rating']}, orders: {g['total_orders']})"
                for g in market_data[:10]
            ])
            
            prompt = f"""Analyze this gig and recommend optimal pricing:

Gig Details:
- Title: {gig_data['title']}
- Category: {gig_data['category']}
- Delivery Time: {gig_data.get('delivery_days', 3)} days
- Seller Trust Score: {gig_data.get('seller_trust_score', 5.0)}

Market Comparison:
{market_summary}

Recommend:
1. Competitive price point
2. Pricing strategy (premium/competitive/budget)
3. Justification

Respond in JSON:
{{
    "recommended_price": 250,
    "price_range": {{"min": 150, "max": 400}},
    "strategy": "competitive",
    "reasoning": "...",
    "market_position": "..."
}}"""

            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(message.content[0].text)
            return result
            
        except Exception as e:
            print(f"AI pricing error: {e}")
            return {
                "recommended_price": 200,
                "price_range": {"min": 100, "max": 500},
                "strategy": "competitive",
                "reasoning": "Default pricing",
                "market_position": "mid-range"
            }
    
    # ==================== AUTOMATED DISPUTE RESOLUTION ====================
    
    def analyze_dispute(self, buyer_claim: str, seller_response: str, order_data: Dict) -> Dict:
        """
        Use Claude to analyze disputes and suggest fair resolutions
        """
        try:
            prompt = f"""Analyze this marketplace dispute and suggest a fair resolution:

Order Details:
- Amount: ₹{order_data['amount']}
- Delivery Time: {order_data.get('delivery_days', 'N/A')} days
- Order Status: {order_data['status']}

Buyer's Claim:
{buyer_claim}

Seller's Response:
{seller_response}

Provide:
1. Analysis of both sides
2. Who seems more credible
3. Suggested resolution
4. Refund recommendation (0-100%)

Respond in JSON:
{{
    "analysis": "...",
    "credibility": {{"buyer": 0.0-1.0, "seller": 0.0-1.0}},
    "suggested_resolution": "...",
    "refund_percentage": 0-100,
    "reasoning": "...",
    "action_items": ["action1", "action2"]
}}"""

            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(message.content[0].text)
            return result
            
        except Exception as e:
            print(f"AI dispute analysis error: {e}")
            return {
                "analysis": "Unable to analyze",
                "credibility": {"buyer": 0.5, "seller": 0.5},
                "suggested_resolution": "Manual review required",
                "refund_percentage": 50,
                "reasoning": "Error in analysis",
                "action_items": []
            }
    
    # ==================== SMART RECOMMENDATIONS ====================
    
    def get_personalized_recommendations(self, user_history: List[Dict], available_gigs: List[Dict]) -> List[int]:
        """
        Use AI to recommend gigs based on user behavior
        """
        try:
            history_text = "\n".join([
                f"- Ordered: {h['gig_title']} (category: {h['category']}, rating given: {h.get('rating', 'N/A')})"
                for h in user_history[-10:]  # Last 10 orders
            ])
            
            gigs_text = "\n".join([
                f"ID {g['id']}: {g['title']} - {g['category']} - ₹{g['price']}"
                for g in available_gigs[:30]
            ])
            
            prompt = f"""Based on this user's order history, recommend the most relevant gigs:

User's History:
{history_text}

Available Gigs:
{gigs_text}

Recommend 5-10 gigs that match their preferences and style.

Respond with JSON:
{{"recommended_gig_ids": [1, 5, 8, ...]}}"""

            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(message.content[0].text)
            return result.get("recommended_gig_ids", [])
            
        except Exception as e:
            print(f"AI recommendations error: {e}")
            return [g['id'] for g in available_gigs[:5]]
    
    # ==================== AUTOMATED QUALITY SCORING ====================
    
    def score_delivery_quality(self, delivery_notes: str, expected_quality: str) -> Dict:
        """
        Use AI to assess delivery quality
        """
        try:
            prompt = f"""Assess the quality of this delivery:

Seller's Delivery Notes:
{delivery_notes}

Expected Quality Level:
{expected_quality}

Rate the delivery on:
1. Completeness (0-10)
2. Professionalism (0-10)
3. Communication quality (0-10)
4. Overall score (0-10)

Respond in JSON:
{{
    "completeness": 8,
    "professionalism": 9,
    "communication": 7,
    "overall_score": 8.0,
    "feedback": "...",
    "concerns": ["concern1", ...]
}}"""

            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(message.content[0].text)
            return result
            
        except Exception as e:
            print(f"AI quality scoring error: {e}")
            return {
                "completeness": 7,
                "professionalism": 7,
                "communication": 7,
                "overall_score": 7.0,
                "feedback": "Unable to assess",
                "concerns": []
            }

# Global AI manager instance
ai_manager = AIManager()
