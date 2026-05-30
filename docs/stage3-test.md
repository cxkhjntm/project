# Stage 3 Verification Guide

## Backend Verification

### Health Check
```bash
curl http://localhost:8000/api/health
```

### Discussion API
```bash
# First, create a room with participants
curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Discussion",
    "goal": "设计登录模块",
    "mode": "code_document",
    "output_directory": "/tmp/output",
    "participants": [
      {"role_card_id": "role_orchestrator", "provider_id": "YOUR_PROVIDER_ID"},
      {"role_card_id": "role_pm", "provider_id": "YOUR_PROVIDER_ID"},
      {"role_card_id": "role_architect", "provider_id": "YOUR_PROVIDER_ID"}
    ]
  }'

# Start discussion (SSE stream)
curl -N http://localhost:8000/api/rooms/{room_id}/start

# Get messages
curl http://localhost:8000/api/rooms/{room_id}/messages
```

### Expected Behavior
- [ ] Discussion starts and streams SSE events
- [ ] Thinking events appear before each expert speaks
- [ ] Messages are persisted to database
- [ ] Round counter increments
- [ ] Discussion completes after max rounds

## Frontend Verification

### Discussion Page
- [ ] Page loads and starts discussion
- [ ] Messages appear in real-time
- [ ] Thinking indicators show for each expert
- [ ] Round progress bar updates
- [ ] Error messages display if API fails
- [ ] Completion state shows correctly

## API Documentation

Interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### SSE Connection Issues
- Check CORS configuration
- Verify backend is running on port 8000
- Check browser console for errors

### Database Issues
- Ensure messages table exists
- Check for migration errors
