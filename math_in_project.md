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

# 3. Nhúng một bit bằng AC-QIM trong `cal_AC()`

Hàm `cal_AC()` nhận một hệ số AC đã lượng tử hóa $c$, bước lượng tử QIM
$\Delta$ và bit cần nhúng $b \in \{0,1\}$. Mục tiêu là thay đổi độ lớn của hệ số
đến mức gần nhất mang đúng parity của $b$, đồng thời giữ lại dấu ban đầu của hệ
số.

```python
def cal_AC(ac: int, delta: int, bit: np.uint8) -> int:
    dau = 1
    if ac < 0:
        dau = -1
    tmp = round(abs(ac) / delta)
    if tmp % 2 != bit:
        giam = tmp - 1
        tang = tmp + 1
        if giam < 0:
            tmp = tang
        elif abs(abs(ac) - giam * delta) <= abs(abs(ac) - tang * delta):
            tmp = giam
        else:
            tmp = tang
    return tmp * delta * dau
```

## 3.1. Tách dấu và độ lớn của hệ số

Dấu của hệ số được xác định bởi:

$$
s(c) =
\begin{cases}
-1 & \text{nếu } c < 0 \\
1 & \text{nếu } c \geq 0
\end{cases}
$$

Phần QIM chỉ thao tác trên độ lớn:

$$
m = |c|
$$

Khác với phép hoán vị bit DC ở mục 2, trường hợp $c=0$ không làm mất thông tin
dấu vì AC-QIM không cần khôi phục lại hệ số ban đầu. Code quy ước dấu của 0 là
dương để có thể đẩy hệ số 0 lên một mức QIM dương khi cần nhúng bit 1.

## 3.2. Chia độ lớn thành các mức QIM

Chỉ số mức QIM gần hệ số ban đầu nhất được tính bằng:

$$
t = \operatorname{round}\left(\frac{|c|}{\Delta}\right)
$$

Độ lớn tương ứng với chỉ số $t$ là:

$$
m_t = t\Delta
$$

Parity của $t$ biểu diễn bit được nhúng:

$$
b = t \bmod 2
$$

Vì vậy hai họ mức QIM là:

$$
\mathcal{Q}_0 = \{0, 2\Delta, 4\Delta, 6\Delta, \ldots\}
$$

$$
\mathcal{Q}_1 = \{\Delta, 3\Delta, 5\Delta, 7\Delta, \ldots\}
$$

Nếu $t \bmod 2=b$ thì mức gần nhất đã thuộc đúng họ cần nhúng và không cần đổi
parity của $t$.

## 3.3. Chọn mức gần nhất khi parity chưa đúng

Nếu $t \bmod 2 \neq b$, hai chỉ số kề bên $t-1$ và $t+1$ đều có parity ngược
với $t$, tức cùng parity với bit $b$. Code đặt:

$$
t_{-} = t-1, \qquad t_{+}=t+1
$$

Chỉ số âm không hợp lệ vì nó không thể biểu diễn độ lớn. Tập ứng viên được viết
thành:

$$
\mathcal{C}_b(t)
=
\left\{
k \in \{t-1,t+1\}
\;\middle|\;
k \geq 0,\ k \bmod 2=b
\right\}
$$

Trong các ứng viên hợp lệ, chọn chỉ số làm thay đổi độ lớn của hệ số ít nhất:

$$
q
=
\underset{k \in \mathcal{C}_b(t)}{\operatorname{argmin}}
\left|\,|c|-k\Delta\right|
$$

Nếu hai phía có cùng khoảng cách, code ưu tiên $t-1$ thông qua toán tử `<=`.
Nếu $t-1<0$ thì chỉ còn $t+1$ là ứng viên hợp lệ.

Toàn bộ phép chọn chỉ số có thể viết gọn dưới dạng:

$$
q =
\begin{cases}
t
& \text{nếu } t \bmod 2=b \\
t+1
& \text{nếu } t \bmod 2\neq b \text{ và } t-1<0 \\
t-1
& \text{nếu } t \bmod 2\neq b
  \text{ và }
  \left||c|-(t-1)\Delta\right|
  \leq
  \left||c|-(t+1)\Delta\right| \\
t+1
& \text{trong các trường hợp còn lại}
\end{cases}
$$

## 3.4. Ghép lại dấu của hệ số

Sau khi chọn được $q$, độ lớn mới là:

$$
m' = q\Delta
$$

Hệ số AC sau khi nhúng là:

$$
c' = s(c)\,q\Delta
$$

Đây chính là biểu thức được trả về bởi:

```python
return tmp * delta * dau
```

Do $|c'|/\Delta=q$ và $q \bmod 2=b$, bit có thể được trích lại bằng:

$$
\hat{b}
=
\operatorname{round}\left(\frac{|c'|}{\Delta}\right)
\bmod 2
$$

## 3.5. Ví dụ với $c=7$ và $\Delta=3$

Chỉ số QIM ban đầu là:

$$
t
=
\operatorname{round}\left(\frac{7}{3}\right)
=2
$$

Nếu cần nhúng bit 0 thì $2 \bmod 2=0$, do đó giữ $q=2$:

$$
c' = 1 \times 2 \times 3 = 6
$$

Nếu cần nhúng bit 1 thì xét hai ứng viên $q=1$ và $q=3$:

$$
|7-1\times3|=4
$$

$$
|7-3\times3|=2
$$

Vì mức 9 gần 7 hơn mức 3 nên chọn $q=3$:

$$
c' = 1 \times 3 \times 3 = 9
$$

Nếu hệ số đầu vào là $c=-7$, cùng phép chọn độ lớn được thực hiện nhưng dấu âm
được ghép lại ở cuối, tạo kết quả tương ứng là $-6$ hoặc $-9$.

## 3.6. Cơ chế lưu hệ số stegno trong file `.npz`

Gọi $C$ là tensor hệ số DCT đã lượng tử hóa của ba kênh và $C'$ là tensor sau
khi AC-QIM sửa các carrier trên kênh Y. Ảnh stegno được dựng bằng biến đổi ngược:

$$
I' = \operatorname{RGB}
\left(
\operatorname{IDCT}(C')
\right)
$$

Khi $I'$ được làm tròn về pixel 8 bit, một số giá trị bị làm tròn hoặc chặn vào
đoạn $[0,255]$. Nếu đọc ảnh rồi DCT và lượng tử hóa lại, tensor thu được chỉ là
một xấp xỉ của $C'$:

$$
\widehat{C}'
=
\operatorname{Quantize}
\left(
\operatorname{DCT}
\left(
\operatorname{YCbCr}(I')
\right)
\right)
$$

Thông thường:

$$
\widehat{C}' \neq C'
$$

Sai lệch này có thể làm parity QIM đổi và khiến payload bị sai. Pipeline hiện
tại tránh sai lệch đó bằng cách lưu trực tiếp tensor $C'$:

```python
np.savez_compressed(steg_path, heso=enc_heso)
```

File `.npz` là một container nén của NumPy. Nó không lưu trực tiếp chuỗi text;
nó lưu chính xác mảng hệ số sau khi các bit đã được nhúng. Khi trích payload,
pipeline tải lại mảng này:

```python
with np.load(steg_path, allow_pickle=False) as steg_data:
    heso = steg_data["heso"].copy()
```

Sau đó `extract()` tái tạo thứ tự carrier từ `key`, `nonce` và cấu hình, rồi đọc
parity trực tiếp trên $C'$. Vì không có bước dựng ảnh rồi DCT lại nên:

$$
\widehat{C}' = C'
$$

và payload được khôi phục đúng trong phạm vi demo.

Đổi lại, đây là cơ chế **steganography có sidecar**, chưa phải giấu tin tự chứa
hoàn toàn trong ảnh. Người nhận cần cả ảnh stegno, JSON và file `.npz`. Nếu bỏ
`.npz`, thuật toán phải được cải tiến để parity vẫn ổn định sau chuỗi IDCT, làm
tròn pixel, chuyển màu và DCT lại; chỉ tăng $\Delta$ trong cách cài đặt hiện tại
chưa bảo đảm khôi phục nguyên payload.
