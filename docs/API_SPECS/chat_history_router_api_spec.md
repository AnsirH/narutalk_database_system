# Chat History Router API 명세서

## 개요
채팅 세션 및 대화 기록을 관리하는 API입니다. 사용자의 채팅 세션 생성, 메시지 저장, 대화 기록 조회 등의 기능을 제공합니다.

## 기본 정보
- **Base URL**: `/chat`
- **Content-Type**: `application/json`
- **인증**: JWT 토큰 기반

## API 엔드포인트

### 1. 메시지 저장
**POST** `/chat/messages`

#### 헤더
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 요청 본문
```json
{
  "session_id": "session_123",
  "employee_id": 1,
  "role": "user",
  "message_text": "안녕하세요, 매출 현황을 알려주세요.",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

#### 파라미터 설명
- **session_id**: 채팅 세션 ID (문자열)
- **employee_id**: 직원 ID (정수)
- **role**: 메시지 역할 ("user" 또는 "assistant")
- **message_text**: 메시지 내용 (텍스트)
- **expires_at**: 만료 시간 (선택사항, ISO 8601 형식)

#### 응답
```json
{
  "message_id": "msg_456",
  "session_id": "session_123",
  "employee_id": 1,
  "role": "user",
  "message_text": "안녕하세요, 매출 현황을 알려주세요.",
  "expires_at": "2024-12-31T23:59:59Z",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### 사용 예시
```bash
curl -X POST "http://localhost:8010/chat/messages" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_123",
    "employee_id": 1,
    "role": "user",
    "message_text": "안녕하세요, 매출 현황을 알려주세요.",
    "expires_at": "2024-12-31T23:59:59Z"
  }'
```

---

### 2. 대화 기록 조회
**GET** `/chat/messages/{session_id}`

#### 헤더
```
Authorization: Bearer <access_token>
```

#### 응답
```json
[
  {
    "message_id": "msg_456",
    "session_id": "session_123",
    "employee_id": 1,
    "role": "user",
    "message_text": "안녕하세요, 매출 현황을 알려주세요.",
    "expires_at": "2024-12-31T23:59:59Z",
    "created_at": "2024-01-01T12:00:00Z"
  },
  {
    "message_id": "msg_457",
    "session_id": "session_123",
    "employee_id": 1,
    "role": "assistant",
    "message_text": "2024년 매출은 15% 증가했습니다.",
    "expires_at": "2024-12-31T23:59:59Z",
    "created_at": "2024-01-01T12:01:00Z"
  }
]
```

#### 사용 예시
```bash
curl -X GET "http://localhost:8010/chat/messages/session_123" \
  -H "Authorization: Bearer <access_token>"
```

---

### 3. 세션 정보 조회
**GET** `/chat/sessions/{session_id}`

#### 헤더
```
Authorization: Bearer <access_token>
```

#### 응답
```json
{
  "session_id": "session_123",
  "employee_id": 1,
  "session_title": "매출 현황 문의",
  "created_at": "2024-01-01T12:00:00Z",
  "last_activity": "2024-01-01T12:01:00Z",
  "is_archived": false,
  "archived_at": null
}
```

#### 사용 예시
```bash
curl -X GET "http://localhost:8010/chat/sessions/session_123" \
  -H "Authorization: Bearer <access_token>"
```

---

### 4. 사용자 세션 목록 조회
**GET** `/chat/sessions/user/{employee_id}`

#### 헤더
```
Authorization: Bearer <access_token>
```

#### 응답
```json
[
  {
    "session_id": "session_123",
    "employee_id": 1,
    "session_title": "매출 현황 문의",
    "created_at": "2024-01-01T12:00:00Z",
    "last_activity": "2024-01-01T12:01:00Z",
    "is_archived": false,
    "archived_at": null
  },
  {
    "session_id": "session_124",
    "employee_id": 1,
    "session_title": "직원 정보 문의",
    "created_at": "2024-01-01T13:00:00Z",
    "last_activity": "2024-01-01T13:05:00Z",
    "is_archived": false,
    "archived_at": null
  }
]
```

#### 사용 예시
```bash
curl -X GET "http://localhost:8010/chat/sessions/user/1" \
  -H "Authorization: Bearer <access_token>"
```

---

### 5. 세션 제목 업데이트
**PUT** `/chat/sessions/{session_id}/title`

#### 헤더
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 요청 본문
```json
{
  "session_title": "업데이트된 세션 제목"
}
```

#### 응답
```json
{
  "session_id": "session_123",
  "employee_id": 1,
  "session_title": "업데이트된 세션 제목",
  "created_at": "2024-01-01T12:00:00Z",
  "last_activity": "2024-01-01T12:01:00Z",
  "is_archived": false,
  "archived_at": null
}
```

#### 사용 예시
```bash
curl -X PUT "http://localhost:8010/chat/sessions/session_123/title" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_title": "업데이트된 세션 제목"
  }'
```

---

### 6. 세션 보관
**POST** `/chat/sessions/{session_id}/archive`

#### 헤더
```
Authorization: Bearer <access_token>
```

#### 응답
```json
{
  "session_id": "session_123",
  "employee_id": 1,
  "session_title": "매출 현황 문의",
  "created_at": "2024-01-01T12:00:00Z",
  "last_activity": "2024-01-01T12:01:00Z",
  "is_archived": true,
  "archived_at": "2024-01-01T14:00:00Z"
}
```

#### 사용 예시
```bash
curl -X POST "http://localhost:8010/chat/sessions/session_123/archive" \
  -H "Authorization: Bearer <access_token>"
```

---

### 7. 세션 복원
**POST** `/chat/sessions/{session_id}/restore`

#### 헤더
```
Authorization: Bearer <access_token>
```

#### 응답
```json
{
  "session_id": "session_123",
  "employee_id": 1,
  "session_title": "매출 현황 문의",
  "created_at": "2024-01-01T12:00:00Z",
  "last_activity": "2024-01-01T12:01:00Z",
  "is_archived": false,
  "archived_at": null
}
```

#### 사용 예시
```bash
curl -X POST "http://localhost:8010/chat/sessions/session_123/restore" \
  -H "Authorization: Bearer <access_token>"
```

---

### 8. 세션 삭제
**DELETE** `/chat/sessions/{session_id}`

#### 헤더
```
Authorization: Bearer <access_token>
```

#### 응답
```json
{
  "message": "세션이 성공적으로 삭제되었습니다.",
  "session_id": "session_123"
}
```

#### 사용 예시
```bash
curl -X DELETE "http://localhost:8010/chat/sessions/session_123" \
  -H "Authorization: Bearer <access_token>"
```

---

### 9. 시스템 상태 확인
**GET** `/chat/health`

#### 응답
```json
{
  "status": "healthy",
  "message": "채팅 시스템이 정상 작동 중입니다.",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### 사용 예시
```bash
curl -X GET "http://localhost:8010/chat/health"
```

---

## 메시지 역할 (Role)

### 사용자 메시지
- **role**: "user"
- 사용자가 입력한 메시지
- 질문, 요청, 응답 등

### 어시스턴트 메시지
- **role**: "assistant"
- 시스템이 생성한 응답
- AI 답변, 시스템 메시지 등

---

## 세션 관리

### 세션 상태
- **활성**: `is_archived = false`
- **보관**: `is_archived = true`

### 세션 라이프사이클
1. **생성**: 첫 메시지 저장 시 자동 생성
2. **활성**: 메시지 주고받기
3. **보관**: 필요시 보관 처리
4. **복원**: 보관된 세션 재활성화
5. **삭제**: 완전 제거

---

## 에러 응답

### 400 Bad Request
```json
{
  "detail": "메시지 텍스트가 비어있습니다."
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 404 Not Found
```json
{
  "detail": "세션을 찾을 수 없습니다."
}
```

### 500 Internal Server Error
```json
{
  "detail": "메시지 저장 중 오류가 발생했습니다."
}
```

---

## 데이터 만료 정책

### 메시지 만료
- **expires_at**: 메시지 만료 시간 설정
- **자동 삭제**: 만료된 메시지는 자동 삭제
- **보존 기간**: 기본 30일

### 세션 만료
- **비활성 세션**: 90일 후 자동 보관
- **보관 세션**: 1년 후 자동 삭제

---

## 주의사항

1. **메시지 순서**: created_at 기준으로 정렬
2. **세션 고유성**: session_id는 고유해야 함
3. **권한 확인**: 자신의 세션만 접근 가능
4. **데이터 보존**: 중요한 대화는 별도 백업
5. **성능**: 대용량 메시지는 청킹 처리 