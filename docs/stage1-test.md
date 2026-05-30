# Stage 1 Verification Guide

## Backend Verification

### Health Check
```bash
# Verify server is running
curl http://localhost:8000/api/health
```

### Provider API
```bash
# Create provider
curl -X POST http://localhost:8000/api/providers \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","base_url":"https://api.openai.com/v1","api_key":"sk-test","default_model":"gpt-4o"}'

# List providers
curl http://localhost:8000/api/providers

# Get single provider
curl http://localhost:8000/api/providers/{id}

# Update provider
curl -X PUT http://localhost:8000/api/providers/{id} \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Name"}'

# Delete provider
curl -X DELETE http://localhost:8000/api/providers/{id}

# Test connection
curl -X POST http://localhost:8000/api/providers/{id}/test
```

### Role Card API
```bash
# List all role cards
curl http://localhost:8000/api/role-cards

# List built-in only
curl http://localhost:8000/api/role-cards?builtin=true

# Get single role card
curl http://localhost:8000/api/role-cards/{id}

# Create role card
curl -X POST http://localhost:8000/api/role-cards \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","description":"Test role","expertise":["test"],"responsibilities":["test"],"system_prompt":"You are test"}'

# Update role card
curl -X PUT http://localhost:8000/api/role-cards/{id} \
  -H "Content-Type: application/json" \
  -d '{"description":"Updated description"}'

# Delete role card
curl -X DELETE http://localhost:8000/api/role-cards/{id}

# Copy role card
curl -X POST http://localhost:8000/api/role-cards/{id}/copy \
  -H "Content-Type: application/json" \
  -d '{"new_name":"Copied Role"}'
```

### Built-in Roles
The system ships with 4 built-in role cards:
1. **主持人** - 控制讨论流程，推动专家发言和结论收敛
2. **产品经理** - 明确需求、用户场景、优先级和 MVP 范围
3. **系统架构师** - 设计模块、技术边界和整体流程
4. **文档专家** - 整理讨论结果，生成结构化最终文档

## Frontend Verification

### Settings Page
- [ ] Page loads with provider form
- [ ] Can create new provider
- [ ] Can edit existing provider
- [ ] Can delete provider
- [ ] Can test connection
- [ ] API key is masked in list

### Role Cards Page
- [ ] Page loads with 4 built-in roles
- [ ] Can create new role card
- [ ] Can edit custom role card
- [ ] Cannot edit built-in role card
- [ ] Can copy role card
- [ ] Can delete custom role card
- [ ] Cannot delete built-in role card
- [ ] Preview modal shows system prompt

### Home Page
- [ ] Page loads correctly
- [ ] Navigation works to Settings and Role Cards

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### Backend issues
- Check Python 3.12+ is installed
- Verify virtual environment is activated
- Check port 8000 is not in use
- Check server logs: `backend/server.log`, `backend/server_error.log`

### Frontend issues
- Check Node.js 18+ is installed
- Run `npm install` in frontend directory
- Check port 5173 is not in use
- Check browser console for errors

### CORS issues
- Ensure backend is running on port 8000
- Check Vite proxy configuration in `vite.config.ts`
- Verify CORS origins in backend config

### Database issues
- Database file: `backend/expert_room.db`
- Check database migrations: `cd backend && alembic upgrade head`
- Reset database: Delete `expert_room.db` and restart server
