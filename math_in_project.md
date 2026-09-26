# 1. Phân tách công thức DCT 2D thành dạng 1D x 1D

Công thức toán học của DCT 2D (loại DCT-2 dùng trong chuẩn nén JPEG) cho một khối ảnh kích thước $8 \times 8$ được phát biểu như sau:

$$
F(u, v) = \alpha(u)\alpha(v) \sum_{x=0}^{7} \sum_{y=0}^{7} f(x, y) \cos \left( \frac{(2x + 1)u\pi}{16} \right) \cos \left( \frac{(2y + 1)v\pi}{16} \right)
$$

Trong đó:
- $f(x, y)$ là giá trị độ sáng pixel tại tọa độ $(x, y)$ trong khối ảnh $8 \times 8$ (sau khi đã trừ 128 để dịch tâm về 0).
- $F(u, v)$ là hệ số DCT tại tần số $(u, v)$ mà chúng ta cần tìm.
- $\alpha(u)$ và $\alpha(v)$ là các hệ số chuẩn hóa:

$$
\alpha(u) = 
\begin{cases} 
\sqrt{\frac{1}{8}} & \text{nếu } u = 0 \\ 
\sqrt{\frac{2}{8}} & \text{nếu } u > 0 
\end{cases}
$$

### Chứng minh tính khả tách (Separability):

Do các hàm số cosin trong công thức trên độc lập hoàn toàn theo từng biến (một hàm chỉ phụ thuộc vào tọa độ ngang $x$ và tần số $u$, hàm còn lại chỉ phụ thuộc vào tọa độ dọc $y$ và tần số $v$), ta có thể viết lại tổng hai chiều dưới dạng tích của hai tổng một chiều lồng nhau:

$$
F(u, v) = \sum_{x=0}^{7} \left[ \alpha(u) \cos \left( \frac{(2x + 1)u\pi}{16} \right) \cdot \left( \sum_{y=0}^{7} f(x, y) \cdot \alpha(v) \cos \left( \frac{(2y + 1)v\pi}{16} \right) \right) \right]
$$

Nếu chúng ta định nghĩa **Ma trận biến đổi DCT 1D** ký hiệu là $T$ kích thước $8 \times 8$, với mỗi phần tử tại dòng $u$ cột $x$ là:

$$
T(u, x) = \alpha(u) \cos \left( \frac{(2x + 1)u\pi}{16} \right)
$$

Thì công thức DCT 2D ở trên thu gọn lại thành:

$$
F(u, v) = \sum_{x=0}^{7} T(u, x) \left( \sum_{y=0}^{7} f(x, y) T(v, y) \right)
$$

# 2. Hoán vị bit thấp của hệ số DC có dấu

## 2.1. Tại sao cách tách `sign(x)` và `abs(x)` làm mất dữ liệu?

Hệ số DC sau lượng tử hóa là số nguyên có dấu: nó có thể âm, dương hoặc bằng 0. Cách cũ tách mỗi hệ số thành:

$$
s = \operatorname{sign}(x), \qquad a = |x|
$$

sau đó chỉ hoán vị các bit của $a$. Vấn đề là một trị tuyệt đối khác 0 có thể tạm trở thành 0 sau khi các bit được chuyển giữa những block. Khi lưu hệ số mã hóa, ta có:

$$
x' = s \times 0 = 0
$$

Đến lúc giải mã, `sign(0)` chỉ trả về 0. Chương trình không thể biết hệ số trước đó là âm hay dương. Ví dụ thực tế đã xảy ra:

```text
DC ban đầu : [-1,  2, -4, 0]
Sau mã hóa : [ 0,  1, -2, 0]
Sau giải mã: [ 0,  2,  0, 0]   <- mất -1 và -4
```

Đối với kênh Cb và Cr, dấu của DC cho biết giá trị màu trung bình của block nằm phía nào so với mức trung tâm 128. Vì vậy mất dấu DC có thể làm ảnh giải mã nhạt màu, sai màu hoặc tiến gần màu xám.

## 2.2. Chia một số nguyên có dấu thành vùng bit cao và bit thấp

Code mới không tách dấu ra khỏi trị tuyệt đối. Nó thao tác trực tiếp trên biểu diễn **bù hai** của số nguyên có dấu.

Hình dưới dùng số nguyên 8 bit và $w=3$ để dễ quan sát. Code thực tế ép hệ số sang `int64`, còn `dc_bit_width` được giới hạn từ 1 đến 31.

![Vị trí bit cao, bit thấp và bit dấu](assets/dc_bit_layout.svg)

Trong ví dụ này:

- $b_7$ là bit dấu.
- Vùng bit cao $H$ gồm $b_7$ đến $b_3$; vùng này không bị hoán vị.
- Vùng bit thấp $L$ gồm $b_2$, $b_1$, $b_0$; chỉ các bit-plane được cấu hình mới bị hoán vị.
- Bit dấu thuộc vùng $H$, do đó nó luôn được giữ lại đối với cấu hình $w$ nhỏ hơn độ rộng số nguyên.

Gọi $w$ là `dc_bit_width`. Mask của vùng bit thấp là:

$$
M = 2^w - 1
$$

Nếu $w=3$ thì:

```text
M  = 00000111₂
~M = 11111000₂    (minh họa trên 8 bit)
```

Ta tách hệ số $x$ bằng hai phép AND:

$$
L = x \mathbin{\&} M
$$

$$
H = x \mathbin{\&} \mathord{\sim}M
$$

Một số ví dụ với $w=3$:

| $x$ | Bù hai 8 bit của $x$ | $H=x\ \&\ \sim M$ | $L=x\ \&\ M$ | $H\ \mathbin{\vert}\ L$ |
|---:|:---:|:---:|:---:|---:|
| $13$ | `00001101` | `00001000` | `00000101` | $13$ |
| $-5$ | `11111011` | `11111000` | `00000011` | $-5$ |
| $0$ | `00000000` | `00000000` | `00000000` | $0$ |

Điểm quan trọng nằm ở hàng $x=-5$: `high_bit` giữ chuỗi `11111` ở phía trái, tức phần mở rộng dấu của số âm. Vì vậy code không cần lưu một mảng dấu riêng.

Không dùng phép dịch phải để lấy $H$. Code giữ $H$ ngay đúng vị trí bằng:

```python
low_bit = values & low_cnt
high_bit = values & ~low_cnt
```

Sau khi thay đổi vùng thấp thành $L'$, hai vùng được ghép lại bằng OR:

$$
x' = H \mathbin{|} L'
$$

```python
rs = high_bit | low_bit
```

## 2.3. Hoán vị diễn ra giữa các block, không phải giữa các vị trí bit

Mỗi phần tử trong `values` là DC của một block được chọn. Với từng bit-plane $i$, code lấy bit thứ $i$ của tất cả những DC đó thành một vector:

$$
B_i[k] = (L_k \gg i) \mathbin{\&} 1
$$

Trong đó $k$ là chỉ số block. Sau đó PRNG tạo một hoán vị $P_i$ và chuyển các bit của bit-plane $i$ giữa những block:

$$
B'_i[k] = B_i[P_i[k]]
$$

![Hoán vị một bit-plane giữa các block DC](assets/dc_bitplane_permutation.svg)

Mỗi bit-plane có một hoán vị riêng vì `rng.permutation()` được gọi lại trong từng vòng lặp. Các bit không đổi vị trí từ $b_0$ sang $b_1$; bit $b_i$ của block này chỉ được chuyển sang vị trí $b_i$ của block khác.

Phần tương ứng trong code mã hóa là:

```python
for i in range(config.dc_bitplanes):
    bits = (low_bit >> i) & 1
    perm = rng.permutation(len(bits))
    scrambled_bits = bits[perm]
    low_bit = low_bit & ~(1 << i)
    low_bit = low_bit | (scrambled_bits << i)
```

Hai dòng cuối thực hiện:

1. Xóa bit cũ tại vị trí $i$ bằng `& ~(1 << i)`.
2. Đặt bit đã hoán vị trở lại đúng vị trí $i$ bằng `| (scrambled_bits << i)`.

## 2.4. Đảo hoán vị khi giải mã

Giải mã tạo lại PRNG từ cùng `key`, `nonce` và label `"dc"`. Nếu thứ tự channel và số lần gọi RNG không đổi, chương trình sinh lại chính xác cùng hoán vị $P_i$.

Với NumPy, nếu mã hóa dùng:

```python
scrambled_bits = bits[perm]
```

thì hoán vị ngược được tính bằng:

```python
reverse_perm = np.argsort(perm)
reversed_bits = scrambled_bits[reverse_perm]
```

Tương đương với:

$$
B_i = P_i^{-1}(B'_i)
$$

Sau khi đảo tất cả các bit-plane, chương trình ghép lại:

$$
x = H \mathbin{|} L
$$

## 2.5. Vì sao phép biến đổi khôi phục chính xác?

Phần $H$ không bị sửa trong cả quá trình. Với từng bit-plane, $P_i$ là một hoán vị nên là một song ánh và luôn có nghịch đảo:

$$
P_i^{-1}(P_i(B_i)) = B_i
$$

Do đó tất cả bit-plane được phục hồi, suy ra $L$ được phục hồi. Cuối cùng:

$$
H \mathbin{|} L = x
$$

Tính đúng không phụ thuộc vào việc một hệ số mã hóa trung gian có bằng 0 hay không. Dấu âm vẫn được biểu diễn trong phần bit cao thay vì được suy đoán lại bằng `sign()`.

## 2.6. Điều kiện để mã hóa và giải mã đối xứng

Để khôi phục đúng, hai phía phải dùng giống nhau:

- `key` và `nonce` để sinh cùng seed.
- Thứ tự `channels`.
- `dc_bit_width` và `dc_bitplanes`.
- `block_mask` và thứ tự các block do `np.nonzero()` trả về.
- Thứ tự gọi `rng.permutation()`.

Ngoài ra phải thỏa mãn:

$$
0 \leq \text{dc\_bitplanes} \leq \text{dc\_bit\_width} \leq 31
$$

Giới hạn 31 bảo đảm kết quả vẫn nằm trong miền `int32` đang dùng để lưu các hệ số DCT. Phép tính trung gian được thực hiện bằng `int64` để tránh lỗi tràn số khi tạo mask và thao tác bit.
