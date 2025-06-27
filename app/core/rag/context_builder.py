from typing import List, Dict, Any, Optional
from app.core.rag.retriever import curriculum_retriever
from app.models.lesson import SkillSpec, GenerationContext
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RAGContextBuilder:
    """Builds enriched context for prompt generation using RAG"""
    
    def __init__(self):
        self.retriever = curriculum_retriever
    
    async def build_lesson_context(
        self,
        topic: str,
        subject: str,
        grade: str,
        curriculum: str,
        skills: List[SkillSpec]
    ) -> GenerationContext:
        """
        Build comprehensive context for lesson generation
        
        Args:
            topic: Lesson topic
            subject: Subject area
            grade: Grade level
            curriculum: Curriculum standard
            skills: Selected thinking skills
            
        Returns:
            GenerationContext with RAG-enriched information
        """
        try:
            # Retrieve general curriculum context
            curriculum_context = await self.retriever.retrieve_context(
                topic=topic,
                subject=subject,
                grade=grade,
                curriculum=curriculum,
                top_k=5
            )
            
            # Build context text from retrieved chunks
            context_text = self._build_context_text(curriculum_context)
            
            # Create generation context
            generation_context = GenerationContext(
                topic=topic,
                grade=grade,
                subject=subject,
                curriculum=curriculum,
                difficulty=0.5,  # Will be set by caller
                curriculum_context=context_text
            )
            
            logger.info(
                "Lesson context built successfully",
                topic=topic,
                context_chunks=len(curriculum_context),
                context_length=len(context_text)
            )
            
            return generation_context
            
        except Exception as e:
            logger.error("Error building lesson context", error=str(e))
            # Return basic context without RAG enhancement
            return GenerationContext(
                topic=topic,
                grade=grade,
                subject=subject,
                curriculum=curriculum,
                difficulty=0.5
            )
    
    async def build_block_context(
        self,
        skill: SkillSpec,
        base_context: GenerationContext
    ) -> str:
        """
        Build specific context for a single block generation
        
        Args:
            skill: The thinking skill for this block
            base_context: Base lesson context
            
        Returns:
            Enriched context string for prompt
        """
        try:
            # Get skill-specific examples and strategies
            skill_context = await self.retriever.retrieve_by_skill(
                skill_name=skill.name,
                block_type=skill.block_type,
                subject=base_context.subject,
                top_k=3
            )
            
            # Combine base context with skill-specific context
            context_parts = []
            
            # Add curriculum context if available
            if base_context.curriculum_context:
                context_parts.append("**Curriculum Information:**")
                context_parts.append(base_context.curriculum_context)
            
            # Add skill-specific examples
            if skill_context:
                context_parts.append(f"**{skill.name} Activity Examples:**")
                for example in skill_context:
                    if example.get('example_activity'):
                        context_parts.append(f"- {example['example_activity']}")
            
            # Add skill description and guidance
            context_parts.append(f"**About {skill.name}:**")
            context_parts.append(skill.description)
            context_parts.append(f"Example question: {skill.example_question}")
            
            enhanced_context = "\n\n".join(context_parts)
            
            logger.debug(
                "Block context built",
                skill=skill.name,
                block_type=skill.block_type,
                context_length=len(enhanced_context)
            )
            
            return enhanced_context
            
        except Exception as e:
            logger.error("Error building block context", error=str(e), skill=skill.name)
            # Return minimal context
            return f"Create a {skill.block_type} activity using the thinking skill '{skill.name}'. {skill.description}"
    
    def _build_context_text(self, context_chunks: List[Dict[str, Any]]) -> str:
        """Build readable context text from retrieved chunks"""
        if not context_chunks:
            return ""
        
        context_parts = []
        seen_content = set()  # Avoid duplicate content
        
        for chunk in context_chunks:
            content = chunk.get('content', '').strip()
            if content and content not in seen_content:
                source_info = ""
                if chunk.get('source'):
                    source_info = f" (Source: {chunk['source']})"
                
                context_parts.append(f"• {content}{source_info}")
                seen_content.add(content)
        
        if context_parts:
            return "\n".join(context_parts)
        else:
            return ""
    
    def _extract_key_concepts(self, context_text: str) -> List[str]:
        """Extract key concepts from curriculum context (simple implementation)"""
        # This is a basic implementation - could be enhanced with NLP
        if not context_text:
            return []
        
        # Look for capitalized terms, terms in quotes, etc.
        import re
        
        # Find quoted terms
        quoted_terms = re.findall(r'"([^"]*)"', context_text)
        
        # Find capitalized multi-word terms (likely concepts)
        concept_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        capitalized_terms = re.findall(concept_pattern, context_text)
        
        # Combine and filter
        all_terms = quoted_terms + capitalized_terms
        key_concepts = [term for term in all_terms if len(term.split()) <= 3 and len(term) > 3]
        
        # Return unique concepts, limited to most relevant
        return list(set(key_concepts))[:10]


# Global instance
rag_context_builder = RAGContextBuilder()