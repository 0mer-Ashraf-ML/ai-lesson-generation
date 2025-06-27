# Structural Learning AI Backend

AI-powered lesson planning system using the Structural Learning Framework's 33 thinking skills to generate pedagogically-structured lesson plans.

## 🎯 Features

- **AI-Generated Lesson Plans**: Create complete lesson plans with MapIt, SayIt, and BuildIt activities
- **Thinking Skills Framework**: Uses 33 color-coded thinking skills for cognitive progression
- **RAG-Enhanced Content**: Curriculum-aligned content using Pinecone vector search
- **Supabase Integration**: User management and lesson persistence
- **Extensible Architecture**: Built for easy addition of new features

## 🏗️ Architecture

```
Teacher Input → Skill Selection → RAG Context → LLM Generation → Structured Lesson Plan
```

### Core Components:
- **Skill Selector**: Chooses appropriate thinking skills based on difficulty
- **RAG System**: Retrieves curriculum-aligned context using Pinecone
- **Block Generator**: Creates MapIt/SayIt/BuildIt activities using OpenAI
- **Storage Service**: Manages lesson persistence with Supabase

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key
- Pinecone account
- Supabase project

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd structural-learning-mvp
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

4. **Set up Supabase database**
```bash
python scripts/setup_supabase.py
```

5. **Set up Pinecone index**
```bash
python scripts/setup_pinecone.py
```

6. **Run the application**
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## 📋 Environment Configuration

Required environment variables:

```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Pinecone
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=structural-learning-curriculum

# Supabase
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# App Settings
SECRET_KEY=your_secret_key_for_jwt
CORS_ORIGINS=http://localhost:3000,https://your-frontend-domain.com
```

## 🔧 API Usage

### Generate a Lesson Plan

```bash
POST /lessons/generatePlan
```

**Request Body:**
```json
{
  "grade": "Year 4",
  "curriculum": "UK KS2",
  "subject": "Science",
  "topic": "States of Matter",
  "difficulty": 0.6,
  "step_count": 3
}
```

**Response:**
```json
{
  "lesson_id": "lesson-abc123",
  "topic": "States of Matter",
  "grade": "Year 4",
  "subject": "Science",
  "blocks": [
    {
      "id": "block-001",
      "type": "MapIt",
      "title": "Categorising States of Matter",
      "description": "Use a Venn diagram to group solids, liquids, and gases...",
      "steps": ["List examples", "Group by properties", "Discuss differences"],
      "skill": {
        "name": "Categorise",
        "color": "Blue",
        "icon_url": "https://cdn.structural-learning.com/icons/blue_categorise.svg",
        "category": "Organizing Ideas"
      },
      "supporting_question": "What properties help us group materials?",
      "media": ["https://cdn.structural-learning.com/templates/venn-diagram.png"]
    }
  ],
  "metadata": {
    "skills_used": ["Categorise", "Explain", "Judge"],
    "cognitive_progression": ["Blue", "Yellow", "Red"],
    "estimated_duration": "45 minutes",
    "difficulty_level": "Proficient"
  }
}
```

### Other Endpoints

- `GET /lessons/` - Get user's lessons
- `GET /lessons/{lesson_id}` - Get specific lesson
- `GET /health/` - Health check
- `GET /health/detailed` - Detailed system health

## 🎨 Thinking Skills Framework

The system uses 5 color-coded categories of thinking skills:

### 🟢 Green - Getting Started
- **Purpose**: Initial engagement, prior knowledge activation
- **Skills**: Identify, Retrieve, Eliminate, Extract
- **Usage**: Lesson opening, foundation setting

### 🔵 Blue - Organizing Ideas  
- **Purpose**: Structuring information, making connections
- **Skills**: Categorise, Compare, Rank, Sequence, Connect
- **Usage**: During exploration, sorting information

### 🟡 Yellow - Critical Thinking
- **Purpose**: Deep analysis, evidence-based reasoning
- **Skills**: Explain, Validate, Exemplify, Verify, Amplify
- **Usage**: Mid-lesson comprehension checks

### 🟠 Orange - Communicating Understanding
- **Purpose**: Language development, vocabulary building
- **Skills**: Verbs, Adverbs, Adjectives, Conjunctions, Target Vocabulary
- **Usage**: Focus on precise expression

### 🔴 Red - Applying Knowledge
- **Purpose**: Creative application, synthesis, evaluation
- **Skills**: Hypothesise, Judge, Combine, Imagine, Integrate, etc.
- **Usage**: End of lesson, assessment, higher-order thinking

## 🧩 Block Types

### MapIt Activities
Visual thinking using graphic organizers:
- Venn diagrams, mind maps, flow charts
- Used with Blue skills (organizing information)
- Example: Compare states of matter using Venn diagram

### SayIt Activities  
Discussion and oracy-focused:
- Structured conversations, debates, explanations
- Used with Yellow/Orange skills (critical thinking/language)
- Example: Explain the water cycle with evidence

### BuildIt Activities
Hands-on construction and creation:
- Physical building, creative projects, problem-solving
- Used with Red skills (applying knowledge)
- Example: Design a solution to reduce plastic waste

## 🔍 Development

### Project Structure
```
app/
├── api/routes/          # FastAPI endpoints
├── core/                # Core business logic
│   ├── skills/         # Skill selection & metadata
│   ├── rag/           # Vector search & context
│   └── generation/    # LLM & prompt management
├── services/          # High-level orchestration
├── models/           # Pydantic data models
├── database/         # Supabase integration
└── utils/           # Utilities & exceptions

data/
├── skills/          # Skill definitions & metadata
├── prompts/        # LLM prompt templates
└── schemas/       # JSON schemas

scripts/           # Setup & maintenance scripts
```

### Running Tests
```bash
pytest tests/
```

### Docker Development
```bash
docker-compose up -d
```

## 🚀 Deployment

### Environment Variables for Production
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### Health Monitoring
The application provides health check endpoints for monitoring:
- `/health/` - Basic health check
- `/health/detailed` - Service-specific health status

## 🔮 Future Extensions

The architecture is designed for easy extension:

### Ready to Add:
- **Feedback Collection**: Teacher ratings for RLHF
- **Block Regeneration**: Regenerate individual blocks
- **Prompt Versioning**: A/B test different prompts
- **Multiple LLMs**: Claude fallback integration
- **Advanced RAG**: Document reranking, multi-vector search
- **Analytics Dashboard**: Usage patterns and insights

### Extension Points:
```python
# Add new LLM client
class ClaudeClient(LLMClient):
    async def generate(self, prompt: str) -> Dict[str, Any]:
        # Implementation

# Add feedback collection
class FeedbackService:
    async def collect_feedback(self, lesson_id: str, feedback: Dict):
        # Implementation

# Add prompt versioning
class VersionedPromptBuilder(PromptBuilder):
    def get_prompt_version(self, version: str) -> str:
        # Implementation
```

## 📚 Resources

- [Structural Learning Framework](https://structural-learning.com)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Pinecone Documentation](https://docs.pinecone.io)
- [Supabase Documentation](https://supabase.com/docs)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.