#!/usr/bin/env python3
"""
Test script to verify the implementation of cognitive complexity levels
"""

import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.models.lesson import SkillSpec, GenerationContext
from app.core.generation.block_generator import block_generator
from app.core.skills.enhanced_metadata import enhanced_skill_metadata
from app.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

async def test_complexity_levels():
    """Test generating blocks with different complexity levels"""
    
    # Create test skills for each color
    test_skills = [
        SkillSpec(
            name="Retrieve",
            color="Green",
            block_type="MapIt",
            example_question="What do we already know about this topic?",
            description="Get information from memory",
            icon_url="https://cdn.structural-learning.com/icons/green_retrieve.svg"
        ),
        SkillSpec(
            name="Categorise",
            color="Blue",
            block_type="MapIt",
            example_question="How can we group these items?",
            description="Sort items into groups based on shared characteristics",
            icon_url="https://cdn.structural-learning.com/icons/blue_categorise.svg"
        ),
        SkillSpec(
            name="Explain",
            color="Yellow",
            block_type="SayIt",
            example_question="Can you explain how this works?",
            description="Communicate understanding clearly with supporting evidence",
            icon_url="https://cdn.structural-learning.com/icons/yellow_explain.svg"
        ),
        SkillSpec(
            name="Hypothesise",
            color="Red",
            block_type="BuildIt",
            example_question="What do you think will happen if...?",
            description="Make predictions based on evidence and test them",
            icon_url="https://cdn.structural-learning.com/icons/red_hypothesise.svg"
        )
    ]
    
    # Create test context
    context = GenerationContext(
        topic="Healthy Eating",
        grade="Year 4",
        subject="Science",
        curriculum="UK KS2",
        difficulty=0.5
    )
    
    # Test each complexity level
    complexity_levels = ["getting_started", "thinking_harder", "stretching_thinking"]
    results = []
    
    # Just test one skill to keep it simple
    test_skill = test_skills[0]  # Use Retrieve skill
    
    for complexity_level in complexity_levels:
        logger.info(f"Testing {test_skill.name} ({test_skill.color}) at {complexity_level} level")
        
        try:
            # Generate a block directly with complexity level
            # First create the enhanced content with complexity level
            enhanced_content = {
                "title": f"{complexity_level.replace('_', ' ').title()} Healthy Eating Activity",
                "description": "Students will retrieve information about healthy eating habits.",
                "steps": [
                    "Step 1: Think about healthy foods you know",
                    "Step 2: Share with a partner",
                    "Step 3: Create a list of healthy foods"
                ],
                "supporting_question": "What healthy foods do you eat regularly?",
                "complexity_level": complexity_level
            }
            
            # Get scaffold resources
            scaffold_resources = {
                "pdfs": [],
                "image": None,
                "video": None
            }
            
            # Generate block using block generator
            block = block_generator._build_enhanced_lesson_block(
                generated_content=enhanced_content,
                skill=test_skill,
                llm_metadata={"model": "test"},
                scaffold_resources=scaffold_resources
            )
            
            # Verify complexity level
            if block.complexity_level != complexity_level:
                logger.warning(f"Complexity level mismatch: expected {complexity_level}, got {block.complexity_level}")
            
            # Log result
            result = {
                "skill": test_skill.name,
                "color": test_skill.color,
                "block_type": test_skill.block_type,
                "complexity_level": block.complexity_level,
                "complexity_display_name": block.complexity_display_name,
                "title": block.title,
                "supporting_question": block.supporting_question
            }
            
            results.append(result)
            logger.info(f"Successfully generated {complexity_level} block for {test_skill.name}")
            
        except Exception as e:
            logger.error(f"Error generating block for {test_skill.name} at {complexity_level}", error=str(e))
    
    # Save results to file
    output_dir = Path(__file__).parent.parent / "data" / "test_output"
    output_dir.mkdir(exist_ok=True, parents=True)
    
    output_file = output_dir / "complexity_levels_test.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Test results saved to {output_file}")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_complexity_levels())
    print(f"Test complete with {len(results)} blocks generated")