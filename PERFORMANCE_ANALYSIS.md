# 📊 Performance Analysis

## 1. Objective

Evaluate the bandwidth efficiency of delta synchronization compared to full file transfer.

---

## 2. Test Scenario

File Size: 10 MB  
Block Size: 4096 bytes  
Modification: 1 block (4 KB)

---

## 3. Traditional Transfer

- Entire file re-uploaded
- Data transferred: 10 MB
- Bandwidth usage: 100%

---

## 4. Delta Synchronization

- Only modified block transmitted
- Data transferred: 4 KB
- Bandwidth usage: 0.04%

---

## 5. Bandwidth Savings

Savings = ((Full Transfer - Delta Transfer) / Full Transfer) × 100

Example:

((10MB - 4KB) / 10MB) × 100 ≈ 99.96%

---

## 6. Concurrency Testing

Tested with multiple clients simultaneously:

- Server maintained responsiveness
- No data corruption
- Threads handled requests independently

---

## 7. Observations

- Delta sync significantly reduces redundant data transmission
- Performance gain increases as file size increases
- Most beneficial for:
  - Incremental backups
  - Cloud storage sync
  - Software updates

---

## 8. Limitations

- Threading may not scale for extremely high client counts
- No encryption currently implemented
- Block size fixed at 4096 bytes

---

## 9. Future Performance Enhancements

- Adaptive block sizing
- Async server model
- Compression before transmission
- TLS encryption benchmarking
