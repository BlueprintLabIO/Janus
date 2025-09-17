# Output Processing Architecture

## Overview

The output module handles response formatting and delivery, distinct from tool calls which create side effects. Output modules are paired with input sources to ensure responses match the originating communication channel.

```
Orchestrator Response → Output Module → Channel Formatter → Response Delivery
```

## Design Principles

### Communication vs Action Separation
- **Output Module**: Pure communication layer - formats and delivers responses
- **Tool Calls**: Action layer - creates side effects and system changes
- **Clear Distinction**: "Say something" vs "Do something"

### Input-Output Pairing
- **Channel Matching**: Responses delivered via same channel as incoming request
- **Context Preservation**: Maintain conversation threads, user references, channel conventions
- **Bidirectional Support**: Handle both request-response and proactive communication

### Format Adaptation
- **Platform-Specific**: Each channel has unique formatting requirements and constraints
- **Rich Media Support**: Images, files, structured content adapted per platform capabilities
- **Progressive Disclosure**: Long responses intelligently truncated or split

### Delivery Reliability
- **Asynchronous Processing**: Handle webhook delays and API rate limits gracefully
- **Retry Logic**: Failed deliveries retried with exponential backoff
- **Delivery Confirmation**: Track successful message delivery for reliability

## Architecture Layers

### 1. Response Router
- **Source Detection**: Identify originating input channel from request context
- **Formatter Selection**: Route to appropriate channel-specific formatter
- **Delivery Strategy**: Choose synchronous vs asynchronous delivery method

### 2. Channel Formatters
- **Slack**: Rich blocks, threading, emoji reactions, file attachments
- **API**: Structured JSON responses with metadata and error handling
- **GitHub**: Markdown comments, code blocks, collapsible details
- **Email**: HTML/plain text with inline images and attachments
- **Web**: Real-time WebSocket updates with interactive elements

### 3. Content Adaptation
- **Length Management**: Respect platform limits (Twitter 280, Slack 40K characters)
- **Markup Translation**: Convert between Markdown, HTML, platform-specific formatting
- **Media Optimization**: Resize images, compress files, convert formats per platform
- **Interactive Elements**: Buttons, quick replies, dropdowns where supported

### 4. Delivery Management
- **Rate Limiting**: Respect platform API limits and avoid flooding
- **Error Handling**: Graceful degradation when delivery fails
- **Threading Logic**: Maintain conversation context in threaded discussions
- **Multi-Part Messages**: Split long responses across multiple messages

## Channel Pairing Examples

### Slack Integration
- **Input**: Slack webhook with channel/thread context
- **Output**: Formatted Slack message with blocks, threading, mentions
- **Features**: Rich formatting, file uploads, interactive buttons

### API Integration  
- **Input**: REST API call with structured request
- **Output**: JSON response with data, metadata, status codes
- **Features**: Machine-readable format, error details, pagination

### GitHub Integration
- **Input**: Webhook from PR/issue events
- **Output**: Markdown comment with code blocks and references  
- **Features**: Syntax highlighting, collapsible sections, @mentions

## Benefits

- **Channel Consistency**: Responses feel native to each platform
- **Context Continuity**: Maintain conversation flow and threading
- **User Experience**: Platform-appropriate formatting and interaction patterns  
- **Reliability**: Robust delivery with failure handling and retries
- **Extensibility**: New channels added without changing core response logic