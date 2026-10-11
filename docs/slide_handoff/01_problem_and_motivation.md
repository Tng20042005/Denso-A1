# Bài toán và động lực

## Bài toán công nghiệp

Fault detector cho rotating machinery cần đại diện đủ cho các trạng thái hỏng, nhưng dữ liệu lỗi đo thực thường rất ít. Một nhà máy có thể thu nhiều giờ normal operation nhưng chỉ có vài fault event, mỗi event lại gắn với một machine, operating condition, maintenance action và sensor setup cụ thể. Việc lấy thêm lỗi thật có thể tốn thời gian, gây rủi ro tài sản và không thể chủ động tái tạo.

Synthetic fault data vì vậy hấp dẫn: nó có thể bổ sung lớp hiếm, mô phỏng condition hoặc tạo balanced training set. Nhưng một waveform “trông giống lỗi” chưa chắc nằm trên real fault manifold. Nếu candidate chứa spectral shortcut, sai resonance/envelope, quá impulsive, near-copy parent hoặc được tune từ test, detector có thể học dấu hiệu giả và giảm hiệu năng trên measured-real faults.

## Các câu hỏi nghiên cứu thực tế

1. Physics-informed synthesis có giúp detector trong chế độ `k={0,1,2}` fault groups hay không?
2. Calibration tối thiểu từ train-only fault groups có sửa được mismatch không?
3. Conditional VAE có học manifold tốt hơn mô hình physics hay không mà không memorize?
4. Conservative transformations của fault đo thật có giữ manifold tốt hơn raw generation không?
5. Nếu không có generator nào đủ bằng chứng, có thể xây một admission gate chung để quyết định candidate nào an toàn và hữu ích trước khi train/deploy không?
6. Gate có phản ứng hợp lý với real-vs-real reference và controlled degradation, hay chỉ là một “always reject” mechanism?

## Vì sao dự án pivot

Pivot không phải thay đổi câu chuyện để che negative result. Chuỗi bằng chứng buộc dự án đổi objective:

- T0 có mismatch rõ: C2ST `1.0`, spectral JS `0.1860`, PSD cosine `0.5133`; envelope anchor và high-frequency energy sai.
- T0-v2 đã freeze trước final evaluation nhưng làm PR-AUC giảm `-0.1573` ở k=1 và `-0.2517` ở k=2 so với E0.
- T2 conditional-VAE pass memorization guard nhưng fail fidelity và giảm utility.
- T3 gần identity hơn, nhưng fail C2ST/near-copy và không hơn E1.

Vì vậy output có giá trị nhất không phải “generator X tốt”, mà là **evidence discipline**: candidate chỉ được dùng nếu validity, fidelity, novelty và measured-real utility cùng đạt.

## Giá trị tiềm năng cho DENSO

Nếu được hiệu chuẩn và prospective-validate bằng DENSO data, SafetyGate có thể hỗ trợ QA trước detector training, phát hiện mismatch/near-copy, chuẩn hóa report và tạo audit trail cho quyết định include/reject synthetic data. Đây là **potential application**, chưa phải lợi ích công nghiệp đã đo được.

## Ranh giới evidence

- CWRU: seeded EDM faults trên public bearing rig.
- Paderborn: measured accelerated-damage bearings, không phải DENSO field faults.
- Không có DENSO factory data trong repository.
- Không có evidence về downtime, maintenance cost hoặc production KPI.

