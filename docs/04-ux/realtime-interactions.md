# Realtime Interactions — WebSocket + Animations

GovFlow sử dụng realtime ở mọi điểm có giá trị — citizen tracking, agent trace, security audit, leadership SLA. Đây là phần tạo "alive" feeling và là điểm polish quan trọng.

## WebSocket architecture

### Connection model

One persistent WS connection per user session. Server pushes events to subscribed topics.

```
Client                                         Server
  │                                               │
  │──CONNECT /api/ws?token=JWT──────────────────▶ │
  │                                               │
  │◀─{type: "connected", session_id}─────────────│
  │                                               │
  │──{type: "subscribe", topic: "case:C-001"}───▶│
  │                                               │
  │◀─{type: "subscribed", topic}──────────────────│
  │                                               │
  │   ... server pushes events as they happen ...  │
  │                                               │
  │◀─{type: "agent_step", ...}────────────────────│
  │◀─{type: "graph_update", ...}──────────────────│
  │◀─{type: "case_status_change", ...}────────────│
  │                                               │
  │──{type: "unsubscribe", topic}───────────────▶│
  │                                               │
```

### Topic patterns

- `case:{case_id}` — all events for a specific case
- `dept:{dept_id}:inbox` — dept inbox updates
- `user:{user_id}:notifications` — personal notifications
- `security:audit` — live audit log (security users only)
- `analytics:dashboard` — dashboard metrics updates

### Event types

```typescript
type WSEvent =
  | { type: 'agent_step_start', case_id: string, agent: string, tool: string, timestamp: string }
  | { type: 'agent_step_end', case_id: string, step_id: string, latency_ms: number, tokens: {in, out}, status: 'success' | 'error' }
  | { type: 'graph_update', case_id: string, added_vertices: Vertex[], added_edges: Edge[] }
  | { type: 'case_status_change', case_id: string, old_status: string, new_status: string, reason: string }
  | { type: 'gap_found', case_id: string, gap: Gap }
  | { type: 'permission_denied', resource: string, reason: string, audit_id: string }
  | { type: 'sla_alert', case_id: string, hours_remaining: number }
  | { type: 'consult_request', from: string, to: string, case_id: string }
  | { type: 'opinion_received', case_id: string, from_dept: string }
  | { type: 'decision_made', case_id: string, decision: 'approve' | 'deny' }
  | { type: 'published', case_id: string, doc_number: string }
  | { type: 'notification', user_id: string, title: string, body: string }
```

## Client implementation

### React hook pattern

```typescript
// hooks/useWSTopic.ts
import { useEffect, useRef } from 'react';
import { useWebSocket } from './useWebSocket';

export function useWSTopic<T>(
  topic: string,
  handler: (event: T) => void
) {
  const ws = useWebSocket();
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    const unsub = ws.subscribe(topic, (event) => {
      handlerRef.current(event);
    });
    return unsub;
  }, [ws, topic]);
}

// Usage in component
function CaseTracker({ caseId }: { caseId: string }) {
  const [events, setEvents] = useState<WSEvent[]>([]);

  useWSTopic(`case:${caseId}`, (event) => {
    setEvents((prev) => [...prev, event]);
    if (event.type === 'case_status_change') {
      toast.info(`Trạng thái: ${event.new_status}`);
    }
  });

  return (
    <div>
      {events.map(renderEvent)}
    </div>
  );
}
```

### Auto-reconnect

```typescript
class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private subscribers = new Map<string, Set<Handler>>();

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;  // reset
      // Re-subscribe to all topics
      for (const topic of this.subscribers.keys()) {
        this.ws.send(JSON.stringify({ type: 'subscribe', topic }));
      }
    };

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      const handlers = this.subscribers.get(msg.topic);
      if (handlers) {
        for (const handler of handlers) {
          handler(msg);
        }
      }
    };

    this.ws.onclose = () => {
      // Exponential backoff
      setTimeout(() => {
        this.reconnectDelay = Math.min(
          this.reconnectDelay * 2,
          this.maxReconnectDelay
        );
        this.connect();
      }, this.reconnectDelay);
    };
  }
}
```

## Animation coordination

### Principle: animations must not lag reality

If user sees agent step animation, the data is already persisted. No fake animations.

### Patterns

**1. New item appearing (list / graph)**
```tsx
<AnimatePresence>
  {items.map((item) => (
    <motion.div
      key={item.id}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
    >
      {renderItem(item)}
    </motion.div>
  ))}
</AnimatePresence>
```

**2. Status change (badge color transition)**
```tsx
<motion.div
  animate={{ backgroundColor: statusColor(status) }}
  transition={{ duration: 0.4 }}
>
  {status}
</motion.div>
```

**3. Counter update (smooth increment)**
```tsx
import { useSpring, animated } from '@react-spring/web';

function AnimatedCounter({ value }: { value: number }) {
  const props = useSpring({
    from: { number: 0 },
    to: { number: value },
    config: { duration: 800 }
  });
  return <animated.span>{props.number.to(n => Math.floor(n))}</animated.span>;
}
```

**4. Graph node pulse (on agent step)**
```tsx
function pulseNode(nodeId: string) {
  const element = document.querySelector(`[data-node-id="${nodeId}"]`);
  if (element) {
    element.classList.add('pulse-active');
    setTimeout(() => element.classList.remove('pulse-active'), 600);
  }
}

// CSS
.pulse-active {
  animation: pulseGlow 600ms ease-out;
}

@keyframes pulseGlow {
  0%   { transform: scale(1); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
  50%  { transform: scale(1.1); box-shadow: 0 0 20px 10px rgba(59, 130, 246, 0.4); }
  100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
}
```

**5. Permission denied shake**
```tsx
<motion.div
  animate={denied ? { x: [-4, 4, -4, 4, 0] } : {}}
  transition={{ duration: 0.2 }}
>
  {content}
</motion.div>
```

**6. Toast entrance**
```tsx
<motion.div
  initial={{ opacity: 0, y: 50, scale: 0.9 }}
  animate={{ opacity: 1, y: 0, scale: 1 }}
  exit={{ opacity: 0, scale: 0.8 }}
  transition={{ type: 'spring', damping: 20, stiffness: 300 }}
>
  {toastContent}
</motion.div>
```

**7. Mask dissolve (Scene C demo)**
```tsx
<motion.div
  animate={{
    filter: `blur(${isRevealed ? 0 : 8}px)`,
    opacity: isRevealed ? 1 : 0.4
  }}
  transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
>
  {sensitiveContent}
</motion.div>
```

## Notification patterns

### Citizen push (mobile-first)

When Compliance finds a gap:

1. Backend creates Draft notice (Drafter agent)
2. Backend writes notification record to `notifications` table
3. Background job picks up → Firebase FCM / Zalo OA
4. Citizen receives push in <5 seconds
5. Citizen taps → opens tracking page
6. Tracking page auto-subscribes to `case:{case_id}` topic
7. Any further updates stream live

### In-app notification bell

```tsx
function NotificationBell() {
  const [unread, setUnread] = useState(0);
  const [notifications, setNotifications] = useState([]);

  useWSTopic(`user:${userId}:notifications`, (event) => {
    setNotifications((prev) => [event, ...prev]);
    setUnread((u) => u + 1);
    // Play subtle sound + animation
    playNotificationSound();
  });

  return (
    <Popover>
      <PopoverTrigger>
        <BellIcon />
        {unread > 0 && <Badge>{unread}</Badge>}
      </PopoverTrigger>
      <PopoverContent>
        {notifications.map(n => <NotificationItem {...n} />)}
      </PopoverContent>
    </Popover>
  );
}
```

## Presence + typing indicators (optional nice-to-have)

For Consult feature: show when the receiver is "typing" their opinion.

```tsx
// Leadership viewing a case → show "Chị Hương đang xem"
const [viewers, setViewers] = useState<string[]>([]);

useWSTopic(`case:${caseId}:presence`, (event) => {
  if (event.type === 'user_viewing') {
    setViewers((prev) => [...new Set([...prev, event.user_name])]);
  }
});
```

Skip for hackathon if time-constrained, add for PoC.

## SSE as fallback

For certain read-only streams (like analytics dashboard), Server-Sent Events might be simpler than WebSocket:

```tsx
useEffect(() => {
  const es = new EventSource('/api/dashboard/stream');
  es.onmessage = (event) => {
    const data = JSON.parse(event.data);
    setMetrics(data);
  };
  return () => es.close();
}, []);
```

## Performance considerations

### Throttling

- Agent trace can generate 100+ events per second for complex case
- Throttle client-side rendering to 60fps
- Batch updates in 100ms windows

```typescript
import { throttle } from 'lodash-es';

const handleEvents = throttle((events) => {
  setNodes((prev) => {
    // Batch apply all events
    return applyEvents(prev, events);
  });
}, 16);  // ~60fps
```

### Message size

- Keep WS messages small (<5KB)
- Don't send full vertex data over WS if cached
- Use deltas: `{type: 'edit', id, changes}` instead of full replace

### Scale considerations

For production 1000s of concurrent users:
- WS server: sticky sessions via SLB
- Redis pub/sub for cross-instance broadcasting
- Topic partitioning by department
- Rate limit subscriptions per user

## Testing

- **Test slow connection:** throttle to 3G → ensure graceful degradation
- **Test disconnect/reconnect:** verify re-subscription works
- **Test permission denied mid-stream:** verify UI handles auth expiry
- **Test many concurrent events:** stress test with 100 events/sec to 1 case
- **Test browser tabs backgrounded:** pause animations to save CPU

## Demo polish

Every realtime interaction must:
- Have visual feedback (not silent)
- Feel instant (<200ms perceived latency)
- Animate smoothly (60fps)
- Degrade gracefully on connection loss
- Never block main UI thread

## Demo moment mapping

> For each WS event type, this table names the **exact demo scene** it drives and the **artifact it reveals on screen**. When pitch team asks "which event makes the gap appear in Scene 3?", the answer is here. Drift between this table and [demo-video-storyboard.md](../07-pitch/demo-video-storyboard.md) means someone edited one without the other — fix immediately.
>
> **Linked to:** [artifact-inventory.md Table 3](./artifact-inventory.md#table-3--demo-video-timeline--artifact-first-reveal) for the inverse view (timeline → artifact first-reveal).

| Event type | Demo scene | Timestamp | Artifact revealed | Screen | UI reaction |
|---|---|---|---|---|---|
| `agent_step_start` (Planner) | Scene 3 Frame 1 | 0:41 | #15 AgentStep Planner node | Agent Trace Viewer | Planner node fades in + timeline row illuminates |
| `agent_step_end` (Planner) | Scene 3 Frame 1 | 0:42 | Planner ✓ | Agent Trace Viewer | Planner glow pulse, detail pane shows 892ms + 450/120 tokens |
| `graph_update` (DocAnalyzer → Documents) | Scene 2 Frame 3 / Scene 3 Frame 2 | 0:32-0:45 | #2 Document label + #3 ExtractedEntity | Intake UI + Agent Trace | Row ✓ + entity chips slide-in on Intake UI; Document+Entity nodes fade in on graph |
| `graph_update` (Classifier → MATCHES_TTHC edge) | Scene 3 Frame 2 | 0:52-0:55 | #4 TTHC classification | Agent Trace Viewer | MATCHES_TTHC edge draws with emphasis (500ms) |
| `gap_found` | Scene 3 Frame 3 | 1:03 | #6 Gap vertex (amber) | Agent Trace Viewer + Intake UI + (later) Citizen Portal tracking | Gap node appears with amber pulse + camera auto-pan; amber shake on Intake UI row |
| `graph_update` (LegalLookup → Citation edge) | Scene 3 Frame 3 | 1:04-1:05 | #8 Citation to Article | Agent Trace Viewer | Citation edge draws from Gap to Article node, both purple |
| `case_status_change` (status → "Chờ bổ sung") | Scene 4 Frame 1 | 1:05 | #25 Status change | Citizen Portal tracking | Timeline step fills, status badge color morph to amber |
| `notification` (to citizen) | Scene 4 Frame 1 | 1:06 | #26 Notification push | Citizen Portal (phone view) | Push notification animation on phone mockup |
| `case_status_change` (status → "Đang xử lý") | Scene 5 Frame 1 | 1:25 | #25 Status change | Department Inbox | Card slide-in to "Đang xử lý" column |
| `graph_update` (Router → ASSIGNED_TO edge) | Scene 5 Frame 1 | 1:22-1:26 | #14 Routing decision | Department Inbox + Agent Trace mini | Kanban card animated move + graph edge draws |
| `consult_request` | Scene 5 Frame 2 (or implied) | 1:26 | #12 ConsultRequest | Consult Inbox (Dũng's view) | New list item slides in + counter-animate unread badge |
| `opinion_received` | Scene 5 Frame 2 | 1:30 | #13 Opinion | Compliance WS + Agent Trace | New line item in Legal panel with pulse glow, Opinion node on graph |
| `agent_step_end` (Summarizer) | Scene 5 Frame 3 | 1:36 | #16 Summary card | Leadership Dashboard | Executive summary fades into approve queue card |
| `decision_made` (approve) | Scene 5 Frame 3 | 1:42 | #19 Decision | Leadership Dashboard + Document Viewer | Button glow pulse + state badge transition |
| `agent_step_end` (Drafter) | Scene 6 Frame 1 | 1:48 | #17 Draft document | Document Viewer | PDF preview fade-in with yellow DRAFT ribbon overlay |
| `published` | Scene 6 Frame 2 | 1:55 | #18 PublishedDoc | Document Viewer + Citizen Portal tracking | Green seal stamp animation + QR fade-in on phone |
| `notification` (to citizen — result) | Scene 6 Frame 2 | 1:56 | #26 Notification push | Citizen Portal (phone view) | Push notification "Giấy phép đã sẵn sàng" |
| `case_classified` (Confidential) | Scene 7 Frame 1 | 2:02 | #5 Classification banner | Security Console (any case view) | Sticky top+bottom banner transitions to Confidential blue |
| `permission_denied` (tier=sdk_guard) | Scene 7 Scene A | 2:05 | #20 PermissionDenied Tier 1 | Security Console | Audit row flash red + shake + toast slide-in |
| `permission_denied` (tier=gdb_rbac) | Scene 7 Scene B | 2:08 | #21 PermissionDenied Tier 2 | Security Console | Same pattern, different reason string |
| `mask_applied` (elevation sequence) | Scene 7 Scene C | 2:11-2:15 | #22 Classification mask | Document Viewer (via Security Console harness) | Solid bar → content crossfade on elevation grant |
| `sla_alert` | (not in main video — live Q&A) | — | #11 SLA countdown warning | Leadership Dashboard + Department Inbox | Badge color transition (green → amber → red) + toast if overdue |
| `audit_written` | Scene 7 (continuous) | 2:00-2:15 | #23 AuditEvent | Security Console live log | Row slide-in 200ms + stagger 50ms if batched |

**Subscription plan for demo:**

During pitch, the demo device should pre-subscribe to these topics before the recording starts:
- `case:C-20260412-DEMO` — for Scene 3, 4, 5, 6 (the hero case)
- `user:dung_phap_che:notifications` — for Scene 5 consult loop
- `security:audit` — for Scene 7
- `user:huong_leadership:notifications` — for Scene 5 Dashboard updates

All other topics deferred to save bandwidth.

**Reduced motion compliance** (see [design-tokens.md §4 reduced motion](./design-tokens.md#reduced-motion--legal-requirement)):
- Every animation pattern in this doc respects `prefers-reduced-motion: reduce`
- When reduced motion is active, animations fall back to: instant state change + brief opacity fade (no scale, no translation, no pulse)
- Counter animations fall back to instant value update
- Graph node entry falls back to instant fade-in (no scale, no glow)
- Reduced motion still communicates state — just without kinetic energy
