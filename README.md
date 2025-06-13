# Enhanced UAV Log Viewer 🚁

An advanced UAV log analysis platform powered by cutting-edge AI technologies including **RAG (Retrieval-Augmented Generation)**, **Multimodal AI**, and **Predictive Analytics**.

## 🌟 Enhanced AI Capabilities

### 🧠 RAG-Powered Analysis
- **Vector Database Integration**: ChromaDB for semantic search and retrieval
- **Deep Insights**: LangChain-powered analysis with contextual understanding
- **Source Attribution**: Track analysis sources and evidence
- **Comprehensive Reports**: AI-generated detailed flight reports

### 👁️ Multimodal Dashboard Analysis
- **Computer Vision**: Analyze UAV dashboard screenshots and images
- **Safety Assessment**: Automated safety status evaluation from visual indicators
- **Performance Metrics**: Extract key metrics from dashboard displays
- **Troubleshooting**: Visual problem identification and recommendations

### 🔮 Predictive Analytics
- **Maintenance Forecasting**: Predict when components need maintenance
- **Performance Trends**: Identify degradation patterns over time
- **Failure Prevention**: Early warning system for potential issues
- **Optimization Recommendations**: Improve flight efficiency and safety

### 📊 Comparative Analysis
- **Multi-Flight Comparison**: Compare performance across multiple flights
- **Trend Analysis**: Identify patterns and improvements over time
- **Benchmarking**: Compare against optimal performance metrics
- **Fleet Management**: Analyze multiple UAVs for fleet optimization

## 🚀 Key Features

### Core Analysis Engine
- **Memory-Safe Log Parsing**: Efficient .bin file processing with pymavlink
- **Real-time Analysis**: Stream processing for large log files
- **Comprehensive Metrics**: Battery, GPS, altitude, vibration, and more
- **Error Detection**: Automated identification of flight issues

### Advanced AI Integration
- **Multiple Analysis Modes**: Quick, Detailed, Expert, and Safety-focused
- **Smart Intent Recognition**: Automatically route queries to appropriate AI systems
- **Enhanced LLM Orchestration**: Ollama integration with multiple model support
- **Context-Aware Responses**: Maintain conversation context across interactions

### Modern User Interface
- **Floating Chat Dialog**: Non-intrusive, draggable interface
- **Dual Upload Support**: Both log files and dashboard images
- **Real-time Feedback**: Typing indicators and progress updates
- **Rich Formatting**: Markdown support with enhanced message display
- **Quick Actions**: One-click report generation and analysis

## 🛠️ Technology Stack

### Backend Technologies
- **FastAPI**: High-performance async API framework
- **LangChain**: LLM application framework for RAG implementation
- **ChromaDB**: Vector database for semantic search
- **Sentence Transformers**: Text embeddings for similarity search
- **Ollama**: Local LLM inference with multimodal support
- **PyMAVLink**: UAV log file parsing and analysis

### AI & Machine Learning
- **RAG Architecture**: Retrieval-Augmented Generation for enhanced responses
- **Vector Embeddings**: Semantic search and similarity matching
- **Computer Vision**: Dashboard image analysis and interpretation
- **Predictive Modeling**: Time series analysis for maintenance forecasting
- **Natural Language Processing**: Intent classification and response generation

### Frontend Technologies
- **Vue.js 3**: Reactive frontend framework
- **Modern CSS**: Advanced styling with animations and transitions
- **Responsive Design**: Mobile-friendly interface
- **Real-time Updates**: WebSocket-like experience with polling

## 📋 API Endpoints

### Enhanced Endpoints

#### `POST /upload`
Upload and process UAV log files with enhanced AI analysis
- **RAG Processing**: Automatic vector database indexing
- **Comprehensive Analysis**: Multi-dimensional log evaluation
- **Metadata Extraction**: Rich flight information extraction

#### `POST /chat`
Enhanced chat with multiple AI capabilities
- **Parameters**: `msg`, `logId`, `analysis_mode`
- **Analysis Modes**: `quick`, `detailed`, `expert`, `safety_focused`
- **AI Features**: RAG, multimodal, predictive analysis

#### `POST /analyze-dashboard`
Multimodal dashboard image analysis
- **Computer Vision**: Extract information from dashboard images
- **Safety Assessment**: Automated safety status evaluation
- **Batch Analysis**: Multiple analysis types in one request

#### `POST /generate-report`
Comprehensive flight report generation
- **RAG-Powered**: Deep insights from vector database
- **Multi-Section**: Structured analysis across all flight aspects
- **Actionable Recommendations**: Specific improvement suggestions

#### `POST /rag-query`
Direct RAG system queries
- **Semantic Search**: Vector-based information retrieval
- **Source Documents**: Attribution and evidence tracking
- **Contextual Responses**: LLM-enhanced answer generation

#### `POST /compare-flights`
Multi-flight comparative analysis
- **Performance Comparison**: Side-by-side flight metrics
- **Trend Identification**: Pattern recognition across flights
- **Optimization Insights**: Improvement recommendations

## 🔧 Installation & Setup

### Prerequisites
- **Python 3.9+**
- **Node.js 16+**
- **Ollama** (for LLM inference)
- **Git**

### Backend Setup

1. **Clone and Navigate**
   ```bash
   git clone <repository-url>
   cd UAVLogViewer/server
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup Ollama**
   ```bash
   # Install Ollama (visit https://ollama.ai)
   ollama pull phi3:mini          # For text analysis
   ollama pull llava:latest       # For multimodal analysis
   ```

5. **Configure Environment**
   ```bash
   export OLLAMA_URL=http://localhost:11434
   export OLLAMA_MODEL=phi3:mini
   export VISION_MODEL=llava:latest
   ```

6. **Start Backend Server**
   ```bash
   uvicorn api:app --reload --port 8000
   ```

### Frontend Setup

1. **Navigate to Frontend**
   ```bash
   cd ../  # Back to project root
   ```

2. **Install Dependencies**
   ```bash
   npm install
   ```

3. **Start Development Server**
   ```bash
   npm run serve
   ```

4. **Access Application**
   - Frontend: http://localhost:8080
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 💡 Usage Guide

### Basic Log Analysis
1. **Upload Log File**: Drag and drop a .bin file or click to browse
2. **Wait for Processing**: Enhanced AI analysis with RAG indexing
3. **Ask Questions**: Use natural language to query your flight data
4. **Get Insights**: Receive detailed, source-attributed responses

### Dashboard Analysis
1. **Upload Dashboard Image**: Drag and drop a screenshot of your UAV dashboard
2. **Select Analysis Type**: Choose from general, safety, performance, or troubleshooting
3. **Get Visual Insights**: Receive computer vision-powered analysis
4. **Follow Recommendations**: Act on AI-generated suggestions

### Advanced Features
- **Analysis Modes**: Switch between Quick, Detailed, Expert, and Safety-focused modes
- **Comprehensive Reports**: Generate full flight analysis reports
- **Predictive Analysis**: Get maintenance and performance forecasts
- **Comparative Analysis**: Compare multiple flights for trend analysis

### Quick Actions
- **📋 Report**: Generate comprehensive flight report
- **👁️ Analyze**: Analyze uploaded dashboard image
- **🔮 Predict**: Run predictive maintenance analysis

## 🔍 Analysis Capabilities

### Flight Performance
- **Duration and Distance**: Complete flight metrics
- **Altitude Analysis**: Maximum, minimum, and average altitudes
- **Speed Analysis**: Ground speed and airspeed metrics
- **Flight Mode Tracking**: Mode changes and time in each mode

### System Health
- **Battery Performance**: Voltage, current, and capacity analysis
- **GPS Status**: Satellite count, HDOP, and positioning accuracy
- **Vibration Analysis**: Motor and frame vibration levels
- **Sensor Health**: IMU, compass, and other sensor status

### Safety Assessment
- **Error Detection**: Automated identification of flight issues
- **Risk Analysis**: Safety-critical parameter evaluation
- **Compliance Checking**: Regulatory and safety standard compliance
- **Emergency Procedures**: Failsafe activation and response analysis

### Predictive Insights
- **Maintenance Scheduling**: Component replacement predictions
- **Performance Degradation**: Trend analysis and forecasting
- **Failure Prevention**: Early warning system implementation
- **Optimization Opportunities**: Efficiency improvement suggestions

## 🎯 AI Analysis Modes

### Quick Mode
- **Fast Processing**: Rapid analysis for immediate insights
- **Key Metrics**: Essential flight parameters only
- **Basic Recommendations**: Simple actionable advice

### Detailed Mode (Default)
- **Comprehensive Analysis**: Full RAG-powered investigation
- **Multi-Source Insights**: Vector database and LLM combination
- **Structured Responses**: Organized, detailed information

### Expert Mode
- **Technical Deep-dive**: Advanced technical analysis
- **Professional Insights**: Expert-level recommendations
- **Detailed Diagnostics**: In-depth system evaluation

### Safety-Focused Mode
- **Risk Assessment**: Safety-critical parameter analysis
- **Compliance Checking**: Regulatory standard evaluation
- **Emergency Preparedness**: Failsafe and emergency procedure analysis

## 🔒 Security & Privacy

- **Local Processing**: All AI inference runs locally via Ollama
- **Data Privacy**: No external API calls for sensitive flight data
- **Secure Storage**: Local vector database with encrypted storage options
- **Access Control**: API-level security and authentication ready

## 🚀 Performance Optimizations

- **Streaming Processing**: Handle large log files efficiently
- **Vector Caching**: Fast retrieval from indexed flight data
- **Parallel Processing**: Concurrent analysis for multiple operations
- **Memory Management**: Efficient resource utilization

## 🔮 Future Enhancements

- **Real-time Analysis**: Live flight monitoring and analysis
- **Fleet Management**: Multi-UAV analysis and comparison
- **Custom Models**: Fine-tuned models for specific UAV types
- **Integration APIs**: Connect with popular flight planning software
- **Mobile App**: Native mobile application for field use

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines for:
- **Code Standards**: Python and JavaScript style guides
- **AI Model Integration**: Adding new analysis capabilities
- **Feature Requests**: Suggesting new functionality
- **Bug Reports**: Reporting and fixing issues

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Comprehensive API and usage documentation
- **Community**: Join our Discord for discussions and support
- **Issues**: GitHub Issues for bug reports and feature requests
- **Professional Support**: Commercial support options available

---

**Built with ❤️ for the UAV community**

*Empowering safer, smarter, and more efficient UAV operations through advanced AI analysis.*
