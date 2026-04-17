# GovFlow — Kế Hoạch Phục Hồi Sau Thảm Họa (DR)
# GovFlow — Disaster Recovery Runbook

**Phiên bản / Version:** 1.0
**Ngày cập nhật / Last updated:** 2026-04-16
**Chủ sở hữu / Owner:** GovFlow Infra Team

---

## 1. Mục tiêu Phục hồi / Recovery Objectives

| Hệ thống / System | RTO | RPO | Ghi chú / Notes |
|---|---|---|---|
| Backend/Frontend pods | < 5 phút | 0 | Kubernetes auto-restart |
| Hologres (PostgreSQL) | < 1 giờ | 15 phút | PITR window 7 ngày |
| Alibaba Cloud GDB | < 1 giờ | 6 giờ | Auto-snapshot mỗi 6h |
| OSS (object storage) | < 5 phút | 0 | Versioning + cross-region sync |
| Toàn bộ hệ thống / Full system | **< 1 giờ** | **15 phút** | Worst-case scenario |

---

## 2. Chiến lược Sao lưu / Backup Strategy

### 2.1 GDB (Alibaba Cloud GDB — Gremlin)

- **Auto-snapshot:** Bật tính năng auto-snapshot trong Alibaba Cloud console — chụp mỗi **6 giờ**, lưu **7 ngày**.
- **Manual snapshot:** Chụp thủ công **trước mỗi lần migration schema** (thay đổi nhãn, index, thuộc tính).
- **Lệnh chụp thủ công:**
  ```bash
  aliyun gdb CreateBackup \
    --region ap-southeast-1 \
    --DBInstanceId <instance-id> \
    --BackupMethod Physical
  ```
- **Tham khảo:** https://www.alibabacloud.com/help/en/gdb/user-guide/back-up-and-restore

### 2.2 Hologres (PostgreSQL-compatible)

- **PITR (Point-in-Time Recovery):** Bật trong console, cửa sổ 7 ngày.
- **Manual dump hàng tuần** → OSS cold storage:
  ```bash
  pg_dump -h <host> -U govflow -d govflow -Fc | \
    aliyun oss cp - oss://govflow-prod/backups/hologres/$(date +%Y%m%d).dump
  ```
- **Tham khảo:** https://www.alibabacloud.com/help/en/hologres/user-guide/point-in-time-recovery

### 2.3 OSS (Object Storage Service)

- **Versioning:** Bật `versioning=Enabled` trên bucket `govflow-prod` (lưu tất cả phiên bản object).
- **Cross-region replication:** Sao chép từ Singapore (`ap-southeast-1`) → Hong Kong (`ap-east-1`) với độ trễ < 5 phút.
- **Lifecycle policy:** Phiên bản cũ > 90 ngày chuyển sang cold storage (IA tier), > 365 ngày xóa.
- **Lệnh bật versioning:**
  ```bash
  aliyun oss bucket-versioning --method put oss://govflow-prod \
    --payer requester --version Enabled
  ```

---

## 3. Quy trình Phục hồi / Recovery Procedures

### Kịch bản 1: Pod crash đơn lẻ (backend hoặc frontend)

**Triệu chứng:** Pod ở trạng thái `CrashLoopBackOff` hoặc `Error`.
**Hành động:** Kubernetes tự động khởi động lại pod.
**Xác nhận:**
```bash
kubectl get pods -n govflow -w
kubectl logs -n govflow deployment/govflow-backend --previous
```
**Nếu không tự phục hồi:**
```bash
kubectl rollout undo deployment/govflow-backend -n govflow
kubectl rollout status deployment/govflow-backend -n govflow
```

---

### Kịch bản 2: DB corruption — Phục hồi Hologres từ PITR

**Triệu chứng:** Lỗi consistency, dữ liệu sai, query trả về kết quả bất thường.

**Các bước:**
1. Xác định thời điểm phục hồi (không quá 7 ngày trước):
   ```bash
   # Xem audit log để xác định thời điểm sự cố
   aliyun hologres DescribeHoloDBInstances --region ap-southeast-1
   ```
2. Tạo instance mới từ PITR trong Alibaba Cloud console:
   - Navigatate: Hologres console → Instances → chọn instance → Restore
   - Chọn **Point-in-Time**: `$(date -d "15 minutes ago" +%Y-%m-%dT%H:%M:%SZ)`
3. Cập nhật `HOLOGRES_DSN` trong K8s secret để trỏ đến instance mới:
   ```bash
   kubectl create secret generic govflow-secrets \
     --namespace govflow \
     --from-env-file=.env.prod \
     --dry-run=client -o yaml | kubectl apply -f -
   kubectl rollout restart deployment/govflow-backend -n govflow
   ```
4. Xác nhận bằng row count so sánh:
   ```bash
   python3 scripts/dr_drill.sh --verify-only
   ```

---

### Kịch bản 3: Region failure — Failover sang region dự phòng

**Triệu chứng:** Alibaba Cloud Singapore (`ap-southeast-1`) không phản hồi.

**Các bước:**
1. Xác nhận sự cố qua Alibaba Cloud status page: https://status.alibabacloud.com
2. Kích hoạt region Hong Kong (`ap-east-1`):
   - OSS: dữ liệu đã được đồng bộ cross-region (RPO ~ 5 phút).
   - GDB: restore từ snapshot mới nhất trong region `ap-east-1`.
   - Hologres: khởi tạo instance mới từ manual dump trên OSS.
3. Cập nhật endpoints trong K8s configmap:
   ```bash
   kubectl edit configmap govflow-config -n govflow
   # Thay đổi GDB_ENDPOINT, HOLOGRES_DSN, OSS_ENDPOINT sang region mới
   ```
4. Cập nhật DNS (TTL thấp nhất khả dụng, khuyến nghị 60s):
   - Trỏ `govflow.example.vn` sang Load Balancer IP của region Hong Kong.
5. Rollout restart để áp dụng config mới:
   ```bash
   kubectl rollout restart deployment -n govflow
   ```
6. Kiểm tra health endpoint:
   ```bash
   curl https://govflow.example.vn/healthz
   ```

---

### Kịch bản 4: Ransomware / Data tampering

**Triệu chứng:** Dữ liệu bị mã hóa, sửa đổi trái phép, hoặc audit log bị xóa.

**Các bước:**
1. **Cô lập ngay lập tức:** Scale về 0 pod để ngăn thêm thiệt hại:
   ```bash
   kubectl scale deployment govflow-backend govflow-frontend -n govflow --replicas=0
   ```
2. **Phục hồi OSS:** Dùng object versioning để rollback:
   ```bash
   # Liệt kê các phiên bản của file bị ảnh hưởng
   aliyun oss listver oss://govflow-prod/path/to/object
   # Restore phiên bản cụ thể
   aliyun oss copy oss://govflow-prod/path/to/object?versionId=<ver> \
     oss://govflow-prod/path/to/object
   ```
3. **Kiểm tra audit log:** Xem `audit_events_flat` trong Hologres để xác định tài khoản bị xâm phạm:
   ```sql
   SELECT actor_user_id, action, path, client_ip, created_at
   FROM audit_events_flat
   WHERE created_at > NOW() - INTERVAL '24 hours'
   ORDER BY created_at DESC;
   ```
4. Thu hồi JWT secrets và cấp lại:
   ```bash
   kubectl create secret generic govflow-secrets \
     --namespace govflow \
     --from-literal=JWT_SECRET="$(openssl rand -base64 48)" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```
5. Báo cáo sự cố theo quy định NĐ 13/2023 trong vòng 72 giờ.

---

## 4. DR Drill Checklist (Quarterly)

Thực hiện mỗi quý, ghi lại kết quả trong Confluence/Wiki.

- [ ] Xác nhận auto-snapshot GDB đang chạy và phiên bản mới nhất < 6h tuổi
- [ ] Thực hiện test PITR Hologres trên môi trường staging
- [ ] Kiểm tra cross-region replication OSS: đẩy file test, xác nhận xuất hiện ở region đích trong 5 phút
- [ ] Chạy `scripts/dr_drill.sh` và xác nhận exit 0
- [ ] Thử `kubectl rollout undo` cho cả backend và frontend
- [ ] Kiểm tra thời gian failover thực tế, so với mục tiêu RTO 1 giờ
- [ ] Cập nhật tài liệu này nếu quy trình thay đổi
- [ ] Ghi lại thời gian và kết quả drill, chia sẻ với team

---

## 5. Liên hệ / Contact

| Role | Contact | Notes |
|---|---|---|
| On-call engineer | #govflow-oncall (Slack) | PagerDuty escalation |
| Alibaba Cloud support | https://ticket.console.aliyun.com | Premium support ticket |
| Security incident | security@govflow.example.vn | + VNCERT/CC nếu dữ liệu công dân bị rò rỉ |
| Data protection officer | dpo@govflow.example.vn | NĐ 13/2023 compliance |

---

## 6. Tài liệu tham khảo / References

- Alibaba Cloud GDB Backup: https://www.alibabacloud.com/help/en/gdb/user-guide/back-up-and-restore
- Hologres PITR: https://www.alibabacloud.com/help/en/hologres/user-guide/point-in-time-recovery
- OSS Versioning: https://www.alibabacloud.com/help/en/oss/user-guide/versioning
- OSS Cross-Region Replication: https://www.alibabacloud.com/help/en/oss/user-guide/cross-region-replication
- ACK Cluster Backup: https://www.alibabacloud.com/help/en/ack/ack-managed-and-ack-dedicated/user-guide/back-up-and-restore-applications
- NĐ 13/2023 về bảo vệ dữ liệu cá nhân: https://datalaw.vn/nd13-2023
