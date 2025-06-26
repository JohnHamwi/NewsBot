"""
Enhanced AI Service for NewsBot
Integrates advanced content analysis with existing AI functionality.
Provides comprehensive content intelligence and optimization recommendations.
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from src.services.ai_service import AIService
from src.services.advanced_content_analyzer import (
    AdvancedContentAnalyzer, 
    ContentInsights,
    EmotionalDimension
)
from src.utils.base_logger import base_logger as logger
from src.core.unified_config import unified_config as config


class ContentOptimization:
    """Content optimization recommendations."""
    
    def __init__(self, insights: ContentInsights, original_content: str):
        self.insights = insights
        self.original_content = original_content
        self.recommendations = self._generate_recommendations()
        
    def _generate_recommendations(self) -> Dict[str, List[str]]:
        """Generate optimization recommendations based on analysis."""
        recommendations = {
            "emotional_optimization": [],
            "credibility_enhancement": [],
            "viral_potential_boost": [],
            "cultural_adaptation": [],
            "timing_optimization": [],
            "engagement_strategies": []
        }
        
        # Emotional optimization
        if self.insights.emotional_profile.emotional_intensity < 0.3:
            recommendations["emotional_optimization"].append(
                "Consider adding more emotional language to increase engagement"
            )
        elif self.insights.emotional_profile.emotional_intensity > 0.8:
            recommendations["emotional_optimization"].append(
                "Content is very emotionally intense - consider balancing with factual information"
            )
            
        if self.insights.emotional_profile.manipulation_likelihood > 0.6:
            recommendations["emotional_optimization"].append(
                "High manipulation risk detected - ensure factual accuracy and balanced presentation"
            )
            
        # Credibility enhancement
        if self.insights.credibility_assessment.overall_score < 0.6:
            recommendations["credibility_enhancement"].extend([
                "Add credible sources and citations",
                "Include fact-checking references",
                "Use more neutral, professional language"
            ])
            
        if len(self.insights.credibility_assessment.warning_flags) > 2:
            recommendations["credibility_enhancement"].append(
                "Multiple credibility concerns detected - thorough fact-checking recommended"
            )
            
        # Viral potential optimization
        if self.insights.viral_potential.viral_score < 0.4:
            recommendations["viral_potential_boost"].extend([
                "Add compelling headlines or hooks",
                "Include relatable human interest angles",
                "Consider adding visual elements"
            ])
            
        if self.insights.viral_potential.discussion_potential > 0.7:
            recommendations["engagement_strategies"].append(
                "High discussion potential - prepare for active community management"
            )
            
        # Cultural adaptation
        if len(self.insights.cultural_context.potential_misunderstandings) > 0:
            recommendations["cultural_adaptation"].extend([
                "Review content for cultural sensitivity",
                "Consider providing cultural context for international audiences"
            ])
            
        # Timing optimization
        primary_emotion = self.insights.emotional_profile.primary_emotion
        if primary_emotion in [EmotionalDimension.URGENCY, EmotionalDimension.FEAR]:
            recommendations["timing_optimization"].append(
                "Urgent/fearful content performs better during peak hours (6-9 PM)"
            )
        elif primary_emotion in [EmotionalDimension.HOPE, EmotionalDimension.JOY]:
            recommendations["timing_optimization"].append(
                "Positive content performs well during morning hours (7-10 AM)"
            )
            
        return recommendations


class EnhancedAIService:
    """Enhanced AI service with advanced content analysis capabilities."""
    
    def __init__(self):
        """Initialize the enhanced AI service."""
        self.ai_service = AIService()
        self.content_analyzer = AdvancedContentAnalyzer()
        
        logger.info("🚀 Enhanced AI Service initialized with advanced content analysis")
        
    async def analyze_and_optimize_content(self, content: str, content_type: str = "news") -> Dict[str, Any]:
        """
        Perform comprehensive content analysis and provide optimization recommendations.
        
        Args:
            content: Text content to analyze
            content_type: Type of content (news, social, etc.)
            
        Returns:
            Complete analysis with optimization recommendations
        """
        start_time = time.time()
        logger.info("🧠 Starting enhanced content analysis and optimization")
        
        try:
            # Run parallel analysis
            analysis_tasks = [
                self.content_analyzer.analyze_comprehensive(content, content_type),
                self._analyze_content_structure(content),
                self._generate_seo_insights(content)
            ]
            
            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            advanced_insights, structure_analysis, seo_insights = results
            
            # Handle exceptions
            if isinstance(advanced_insights, Exception):
                logger.error(f"Advanced analysis failed: {advanced_insights}")
                advanced_insights = None
                
            if isinstance(structure_analysis, Exception):
                logger.error(f"Structure analysis failed: {structure_analysis}")
                structure_analysis = {}
                
            if isinstance(seo_insights, Exception):
                logger.error(f"SEO analysis failed: {seo_insights}")
                seo_insights = {}
                
            # Generate optimization recommendations
            optimization = None
            if advanced_insights:
                optimization = ContentOptimization(advanced_insights, content)
                
            # Create comprehensive analysis summary
            analysis_summary = await self._create_comprehensive_summary(
                advanced_insights, structure_analysis, seo_insights, optimization
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            logger.info(f"✅ Enhanced analysis completed in {processing_time:.2f}ms")
            
            return {
                "advanced_insights": advanced_insights,
                "structure_analysis": structure_analysis,
                "seo_insights": seo_insights,
                "optimization": optimization.recommendations if optimization else {},
                "summary": analysis_summary,
                "processing_time_ms": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced content analysis failed: {e}")
            return {
                "error": str(e),
                "processing_time_ms": (time.time() - start_time) * 1000,
                "timestamp": datetime.now().isoformat()
            }
            
    async def _analyze_content_structure(self, content: str) -> Dict[str, Any]:
        """Analyze content structure and readability."""
        try:
            sentences = content.split('.')
            paragraphs = content.split('\n\n')
            words = content.split()
            
            # Basic readability metrics
            avg_sentence_length = len(words) / len(sentences) if sentences else 0
            avg_paragraph_length = len(sentences) / len(paragraphs) if paragraphs else 0
            
            # Content structure analysis
            structure_score = 0.0
            structure_notes = []
            
            # Sentence length analysis
            if 10 <= avg_sentence_length <= 20:
                structure_score += 0.3
                structure_notes.append("Good average sentence length")
            elif avg_sentence_length > 25:
                structure_notes.append("Sentences are too long - consider breaking them down")
            else:
                structure_notes.append("Sentences are very short - consider combining some")
                
            # Paragraph analysis
            if 3 <= avg_paragraph_length <= 6:
                structure_score += 0.3
                structure_notes.append("Good paragraph structure")
            elif avg_paragraph_length > 8:
                structure_notes.append("Paragraphs are too long - break them into smaller chunks")
                
            # Word count analysis
            if 50 <= len(words) <= 300:
                structure_score += 0.4
                structure_notes.append("Good content length for social media")
            elif len(words) > 500:
                structure_notes.append("Content is quite long - consider creating a summary")
                
            return {
                "word_count": len(words),
                "sentence_count": len(sentences),
                "paragraph_count": len(paragraphs),
                "avg_sentence_length": round(avg_sentence_length, 2),
                "avg_paragraph_length": round(avg_paragraph_length, 2),
                "structure_score": min(structure_score, 1.0),
                "structure_notes": structure_notes,
                "readability": "high" if structure_score > 0.7 else "medium" if structure_score > 0.4 else "low"
            }
            
        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")
            return {"error": str(e)}
            
    async def _generate_seo_insights(self, content: str) -> Dict[str, Any]:
        """Generate SEO and discoverability insights."""
        try:
            words = content.lower().split()
            
            # Keyword density analysis
            word_freq = {}
            for word in words:
                if len(word) > 3:  # Only count meaningful words
                    word_freq[word] = word_freq.get(word, 0) + 1
                    
            # Top keywords
            top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # SEO recommendations
            seo_recommendations = []
            
            if len(words) < 50:
                seo_recommendations.append("Content is too short for good SEO - aim for 100+ words")
            elif len(words) > 1000:
                seo_recommendations.append("Very long content - consider adding subheadings and structure")
                
            # Check for question words (good for featured snippets)
            question_words = ['what', 'how', 'why', 'when', 'where', 'who']
            has_questions = any(word in words for word in question_words)
            
            if has_questions:
                seo_recommendations.append("Contains question words - good for featured snippets")
            else:
                seo_recommendations.append("Consider adding question-based content for better discoverability")
                
            return {
                "top_keywords": top_keywords,
                "keyword_density": len(set(words)) / len(words) if words else 0,
                "has_questions": has_questions,
                "seo_score": 0.7 if has_questions and 100 <= len(words) <= 800 else 0.4,
                "recommendations": seo_recommendations
            }
            
        except Exception as e:
            logger.error(f"SEO analysis failed: {e}")
            return {"error": str(e)}
            
    async def _create_comprehensive_summary(self, advanced_insights: ContentInsights,
                                          structure_analysis: Dict, seo_insights: Dict, 
                                          optimization: ContentOptimization) -> Dict[str, Any]:
        """Create a comprehensive analysis summary."""
        try:
            summary = {
                "overall_score": 0.0,
                "key_strengths": [],
                "improvement_areas": [],
                "action_items": [],
                "risk_assessment": "low"
            }
            
            scores = []
            
            # Advanced insights scoring
            if advanced_insights:
                scores.append(advanced_insights.confidence_score)
                
                # Emotional analysis
                if advanced_insights.emotional_profile.emotional_intensity > 0.5:
                    summary["key_strengths"].append("Strong emotional engagement")
                else:
                    summary["improvement_areas"].append("Low emotional engagement")
                    
                # Credibility scoring
                if advanced_insights.credibility_assessment.overall_score > 0.7:
                    summary["key_strengths"].append("High credibility score")
                elif advanced_insights.credibility_assessment.overall_score < 0.4:
                    summary["improvement_areas"].append("Credibility concerns")
                    summary["risk_assessment"] = "medium"
                    
                # Viral potential
                if advanced_insights.viral_potential.viral_score > 0.6:
                    summary["key_strengths"].append("High viral potential")
                    
                # Cultural sensitivity
                if advanced_insights.cultural_context.cultural_sensitivity_score > 0.8:
                    summary["key_strengths"].append("Culturally sensitive content")
                elif advanced_insights.cultural_context.cultural_sensitivity_score < 0.5:
                    summary["improvement_areas"].append("Cultural sensitivity concerns")
                    summary["risk_assessment"] = "high"
                    
            # Structure analysis scoring
            if structure_analysis and "structure_score" in structure_analysis:
                scores.append(structure_analysis["structure_score"])
                if structure_analysis["structure_score"] > 0.7:
                    summary["key_strengths"].append("Well-structured content")
                else:
                    summary["improvement_areas"].append("Content structure needs improvement")
                    
            # SEO scoring
            if seo_insights and "seo_score" in seo_insights:
                scores.append(seo_insights["seo_score"])
                if seo_insights["seo_score"] > 0.6:
                    summary["key_strengths"].append("Good SEO potential")
                else:
                    summary["improvement_areas"].append("SEO optimization needed")
                    
            # Calculate overall score
            if scores:
                summary["overall_score"] = sum(scores) / len(scores)
                
            # Generate action items from optimization
            if optimization and optimization.recommendations:
                for category, recommendations in optimization.recommendations.items():
                    if recommendations:
                        summary["action_items"].extend(recommendations[:2])  # Top 2 per category
                        
            return summary
            
        except Exception as e:
            logger.error(f"Summary creation failed: {e}")
            return {"error": str(e)}
            
    async def get_content_intelligence_report(self, content: str) -> str:
        """Generate a human-readable intelligence report for content."""
        try:
            analysis = await self.analyze_and_optimize_content(content)
            
            if "error" in analysis:
                return f"❌ Analysis failed: {analysis['error']}"
                
            report_lines = [
                "🧠 **CONTENT INTELLIGENCE REPORT**",
                "=" * 50,
                ""
            ]
            
            # Overall assessment
            if "summary" in analysis and "overall_score" in analysis["summary"]:
                score = analysis["summary"]["overall_score"]
                score_emoji = "🟢" if score > 0.7 else "🟡" if score > 0.4 else "🔴"
                report_lines.extend([
                    f"**Overall Score:** {score_emoji} {score:.1%}",
                    ""
                ])
                
            # Advanced insights summary
            if analysis.get("advanced_insights"):
                insights = analysis["advanced_insights"]
                summary = await self.content_analyzer.get_analysis_summary(insights)
                
                report_lines.extend([
                    "📊 **EMOTIONAL ANALYSIS**",
                    f"Primary Emotion: {summary['emotional_summary']['primary_emotion'].title()}",
                    f"Intensity: {summary['emotional_summary']['intensity']}",
                    f"Stability: {summary['emotional_summary']['stability'].title()}",
                    f"Manipulation Risk: {summary['emotional_summary']['manipulation_risk'].title()}",
                    "",
                    "🔍 **CREDIBILITY ASSESSMENT**",
                    f"Overall Score: {summary['credibility_summary']['overall_score']}",
                    f"Reliability: {summary['credibility_summary']['reliability'].title()}",
                    f"Warnings: {summary['credibility_summary']['warning_count']}",
                    "",
                    "🚀 **VIRAL POTENTIAL**",
                    f"Viral Score: {summary['viral_summary']['viral_potential']}",
                    f"Sharing Likelihood: {summary['viral_summary']['sharing_likelihood']}",
                    f"Discussion Potential: {summary['viral_summary']['discussion_potential']}",
                    "",
                    "🌍 **CULTURAL CONTEXT**",
                    f"Sensitivity Score: {summary['cultural_summary']['sensitivity_score']}",
                    f"Cultural References: {summary['cultural_summary']['cultural_references']}",
                    ""
                ])
                
            # Key recommendations
            if "summary" in analysis:
                summary = analysis["summary"]
                
                if summary.get("key_strengths"):
                    report_lines.extend([
                        "✅ **KEY STRENGTHS**",
                        *[f"• {strength}" for strength in summary["key_strengths"][:3]],
                        ""
                    ])
                    
                if summary.get("improvement_areas"):
                    report_lines.extend([
                        "⚠️ **IMPROVEMENT AREAS**",
                        *[f"• {area}" for area in summary["improvement_areas"][:3]],
                        ""
                    ])
                    
                if summary.get("action_items"):
                    report_lines.extend([
                        "🎯 **RECOMMENDED ACTIONS**",
                        *[f"• {action}" for action in summary["action_items"][:5]],
                        ""
                    ])
                    
            # Processing info
            processing_time = analysis.get("processing_time_ms", 0)
            report_lines.extend([
                f"⏱️ Analysis completed in {processing_time:.0f}ms",
                f"🕒 Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Intelligence report generation failed: {e}")
            return f"❌ Failed to generate intelligence report: {str(e)}"
