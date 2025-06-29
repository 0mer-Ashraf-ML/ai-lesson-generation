import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.models.lesson import SkillSpec, GenerationContext
from app.core.generation.block_generator import block_generator
from app.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

async def test_resource_generation():
    """Test generating a lesson block with scaffold resources"""
    
    # Create a test skill
    mapit_skill = SkillSpec(
        name="Categorise",
        color="Blue",
        block_type="MapIt",
        example_question="How can we group these items?",
        description="Sort items into groups based on shared characteristics",
        icon_url="https://cdn.structural-learning.com/icons/blue_categorise.svg"
    )
    
    sayit_skill = SkillSpec(
        name="Explain",
        color="Yellow",
        block_type="SayIt",
        example_question="Can you explain what's happening here?",
        description="Communicate understanding clearly with supporting evidence",
        icon_url="https://cdn.structural-learning.com/icons/yellow_explain.svg"
    )
    
    buildit_skill = SkillSpec(
        name="Hypothesise",
        color="Red",
        block_type="BuildIt",
        example_question="What do you think will happen if we try this?",
        description="Make predictions based on evidence and test them",
        icon_url="https://cdn.structural-learning.com/icons/red_hypothesise.svg"
    )
    
    # Create context
    context = GenerationContext(
        topic="States of Matter",
        grade="Year 4",
        subject="Science",
        curriculum="UK KS2",
        difficulty=0.6
    )
    
    # Generate blocks for each skill type
    skills = [mapit_skill, sayit_skill, buildit_skill]
    blocks = []
    
    for i, skill in enumerate(skills):
        logger.info(f"Generating block for {skill.block_type} - {skill.name}")
        
        block = await block_generator.generate_block(
            skill=skill,
            context=context,
            sequence_order=i
        )
        
        blocks.append(block)
        
        # Log block details
        logger.info(f"Generated {skill.block_type} block:")
        logger.info(f"Title: {block.title}")
        logger.info(f"Description: {block.description}")
        logger.info(f"Resources: {len(getattr(block, 'resources', []))} resources attached")
        
        # Log attached resources
        if hasattr(block, 'resources') and block.resources:
            for j, resource in enumerate(block.resources):
                logger.info(f"  Resource {j+1}: {resource.type} - {resource.name}")
                logger.info(f"  URL: {resource.url}")
        
        logger.info("-" * 50)
    
    # Save the generated blocks to a JSON file for inspection
    output_dir = Path(__file__).parent.parent / "data" / "test_output"
    output_dir.mkdir(exist_ok=True, parents=True)
    
    output_file = output_dir / "test_blocks_with_resources.json"
    with open(output_file, "w") as f:
        json.dump(
            [block.model_dump() for block in blocks],
            f,
            indent=2
        )
    
    logger.info(f"Saved test output to {output_file}")
    
    return blocks

if __name__ == "__main__":
    asyncio.run(test_resource_generation())