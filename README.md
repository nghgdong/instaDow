# instaDow

`instaDow` la CLI de tai post, reel va profile Instagram ve may.

Tool nay ho tro 2 nhom use case chinh:

- Tai 1 media URL cu the nhu `/p/.../` hoac `/reel/.../`
- Tai ca profile bang username hoac profile URL, co ho tro cookies/session de giam loi rate-limit

## Tinh nang

- Tai public post URLs
- Tai public reel URLs
- Tai profile bang username hoac profile URL
- Tai carousel posts
- Tai reels tab rieng voi `--reels-only`
- Luu them caption voi `--write-caption`
- Luu thumbnail voi `--write-thumbnail`
- Xem metadata ma khong tai file voi `--print-info`
- Dung `cookies.txt` Netscape format cho ca media URL va profile
- Ho tro Instagram session qua `--login` va tu dong tai su dung session da luu

## Yeu cau

- Python 3.11 tro len
- Windows, macOS hoac Linux co the chay Python va pip

## Cai dat

Clone repo roi cai editable package:

```powershell
python -m pip install -e .
```

Sau khi cai dat, ban co the chay:

```powershell
instadow --help
```

hoac:

```powershell
python -m instadow --help
```

Xem version:

```powershell
instadow --version
```

## Product-ready features

- Nho config mac dinh qua file JSON local
- Ho tro batch targets qua `--targets-file`
- Co `--self-check` de tu kiem tra moi truong, config, cookies
- Co script build `.exe` cho Windows
- Co the support user tu xa de hon vi config va diagnostics da duoc chuan hoa

## Kien truc tai media

- Media URL truc tiep duoc tai bang `yt-dlp`
- Profile downloads duoc xu ly bang `instaloader` ket hop web session/cookies
- Khi profile dung `--cookies-file`, tool uu tien goi Instagram profile feed API de lay feed thuong on dinh hon
- Reels tab cua profile duoc quet rieng, vi vay neu muon chi lay reels thi nen dung `--reels-only`

## Xac thuc

### Cach 1: Cookies file, khuyen dung cho profile

Neu ban da export duoc file Netscape cookies, day la cach on dinh nhat cho profile:

```powershell
python -m instadow 11_14_42 --cookies-file .\instagram_cookies.txt
```

File cookie hop le thuong co dang:

```text
# Netscape HTTP Cookie File
.instagram.com TRUE / TRUE ... sessionid ...
```

`--cookies-file` duoc ho tro cho:

- media URL truc tiep
- profile by username
- profile by URL
- `--reels-only`

### Cach 2: Dang nhap bang username

Neu khong co cookies file, ban co the cho tool login:

```powershell
python -m instadow 11_14_42 --login your_instagram_username
```

Lan dau tool se login tuong tac va tao session. Cac lan sau tool se tu thu nap lai session da luu.

### Cach 3: Session file rieng

Neu muon tu quan ly session file:

```powershell
python -m instadow 11_14_42 --login your_instagram_username --session-file .\ig.session
```

### Session auto reuse

Sau khi login thanh cong mot lan, tool se co gang:

- nap lai session da luu trong local config
- neu may chi co 1 Instaloader session, tool se tu phat hien va thu dung session do

## Config mac dinh

Tool co the luu cac tuy chon thuong dung thanh mac dinh.

File config mac dinh:

```text
%LOCALAPPDATA%\instadow\config.json
```

Luu config hien tai:

```powershell
python -m instadow --cookies-file .\instagram_cookies.txt --output-dir .\downloads --save-config
```

Xem config dang luu:

```powershell
python -m instadow --show-config
```

Xoa config:

```powershell
python -m instadow --reset-config
```

Dung config file rieng:

```powershell
python -m instadow --config .\seller-config.json --show-config
```

Sau khi da luu config, ban co the goi gon:

```powershell
python -m instadow 11_14_42
```

## Batch mode

Ban co the dat danh sach target trong file text, moi dong mot target:

```text
# targets.txt
11_14_42
https://www.instagram.com/p/POST_ID/
https://www.instagram.com/reel/REEL_ID/
```

Chay batch:

```powershell
python -m instadow --targets-file .\targets.txt
```

Co the ket hop `targets` truyen truc tiep va `--targets-file`. Tool se tu dedupe target trung nhau.

## Cach dung co ban

### Tai 1 post

```powershell
python -m instadow https://www.instagram.com/p/POST_ID/
```

### Tai 1 reel

```powershell
python -m instadow https://www.instagram.com/reel/REEL_ID/
```

### Tai ca profile bang username

```powershell
python -m instadow 11_14_42 --cookies-file .\instagram_cookies.txt
```

### Tai ca profile bang URL

```powershell
python -m instadow https://www.instagram.com/11_14_42/ --cookies-file .\instagram_cookies.txt
```

### Chi tai reels tu profile

```powershell
python -m instadow 11_14_42 --reels-only --cookies-file .\instagram_cookies.txt
```

### Tai nhieu target cung luc

```powershell
python -m instadow `
  -o .\downloads `
  https://www.instagram.com/p/POST_ID/ `
  https://www.instagram.com/reel/REEL_ID/ `
  11_14_42
```

## Cac vi du hay dung

Tai profile va gioi han so bai:

```powershell
python -m instadow 11_14_42 --cookies-file .\instagram_cookies.txt --max-posts 20
```

Chi tai reels va gioi han 5 reel:

```powershell
python -m instadow 11_14_42 --reels-only --cookies-file .\instagram_cookies.txt --max-posts 5
```

Bo qua reels, chi lay feed thuong:

```powershell
python -m instadow 11_14_42 --no-reels --cookies-file .\instagram_cookies.txt
```

Bo qua avatar profile:

```powershell
python -m instadow 11_14_42 --no-profile-pic --cookies-file .\instagram_cookies.txt
```

Luu them caption:

```powershell
python -m instadow 11_14_42 --write-caption --cookies-file .\instagram_cookies.txt
```

Luu them thumbnail:

```powershell
python -m instadow 11_14_42 --write-thumbnail --cookies-file .\instagram_cookies.txt
```

Cap nhat profile va dung som neu gap item da tai:

```powershell
python -m instadow 11_14_42 --fast-update --cookies-file .\instagram_cookies.txt
```

In metadata profile ma khong tai:

```powershell
python -m instadow 11_14_42 --print-info --cookies-file .\instagram_cookies.txt -v
```

Tai media URL can auth:

```powershell
python -m instadow --cookies-file .\instagram_cookies.txt https://www.instagram.com/p/POST_ID/
```

Chan doan moi truong:

```powershell
python -m instadow --self-check
python -m instadow --self-check --cookies-file .\instagram_cookies.txt --targets-file .\targets.txt
```

## Y nghia cac option chinh

- `targets`: media URL, profile URL hoac username
- `--targets-file`: doc danh sach targets tu file text
- `--config`: chi dinh file config JSON rieng
- `--save-config`: luu cac option hien tai thanh mac dinh
- `--show-config`: in config dang luu va config hieu luc
- `--reset-config`: xoa config dang luu
- `--self-check`: in thong tin diagnostics de debug/support
- `-o`, `--output-dir`: thu muc dich, mac dinh la `downloads`
- `-t`, `--template`: ten file cho media URL truc tiep theo template cua `yt-dlp`
- `--profile-template`: mau ten cho asset do Instaloader quan ly, chu yeu huu ich voi asset profile nhu profile pic
- `--cookies-file`: cookies file Netscape format cho media URL hoac profile
- `--login`: username Instagram de login/session mode
- `--session-file`: session file rieng cho Instaloader
- `--write-caption`: luu caption ra file `.txt`
- `--write-thumbnail`: luu thumbnail khi co
- `--print-info`: chi in metadata, khong tai file
- `--max-posts`: gioi han so item moi luot quet profile
- `--no-reels`: bo qua tab reels khi tai profile
- `--reels-only`: chi quet tab reels cua profile
- `--no-profile-pic`: bo qua avatar profile
- `--fast-update`: dung som khi gap item da ton tai
- `-v`, `--verbose`: bat log chi tiet

## Cau truc output

Mac dinh file duoc luu trong `downloads/`.

Vi du:

```text
downloads/
  11_14_42/
    20250828_070153_DN47sPejxAf_01.jpg
    20251212_204951_DSMGvGgj5mu_01.mp4
    20251212_204951_DSMGvGgj5mu.txt
    20251212_204951_DSMGvGgj5mu_01_thumbnail.jpg
```

Quy uoc dat ten hien tai:

- `YYYYMMDD_HHMMSS_shortcode_index.ext`
- captions duoc luu thanh `.txt`
- thumbnail duoc them hau to `_thumbnail`

## Ghi chu quan trong

- Neu ban chay profile mode ma chi thay anh, hay dung `--reels-only` de quet tab reels rieng
- Mot so profile public van co the can cookies/session vi Instagram thay doi rate-limit theo thoi diem
- Van co the xuat hien mot vai dong canh bao `graphql/query 403` tu Instaloader khi doc metadata hoac quet reels, nhung profile download van co the tiep tuc chay
- `--profile-template` khong chi phoi toan bo feed download path hien tai; media profile duoc dat ten theo timestamp + shortcode de on dinh hon

## Troubleshooting

### 1. `Khong the truy cap profile ... khi chua dang nhap`

Profile dang can auth hoac Instagram dang chan anonymous access.

Thu:

```powershell
python -m instadow 11_14_42 --cookies-file .\instagram_cookies.txt
```

### 2. `Please wait a few minutes before you try again`

Instagram dang rate-limit session hien tai.

Huong xu ly:

- doi 10-30 phut roi thu lai
- giam tan suat chay lien tuc
- export lai cookies moi
- dung profile voi `--max-posts` nho hon

### 3. Da login roi nhung van loi

Thu uu tien `--cookies-file` truoc `--login`, vi cookies browser thuong on dinh hon.

### 4. `There are multiple cookies with name, 'csrftoken'`

Ban nay da duoc fix trong CLI. Neu con gap, hay cap nhat repo len commit moi nhat roi chay lai:

```powershell
python -m pip install -e .
```

### 5. `UnicodeEncodeError` tren PowerShell

Ban nay da co fallback JSON escaped trong `--print-info`, nen metadata van in ra duoc.

## Bao mat

- Khong commit `instagram_cookies.txt`, `.session`, hoac credential files len git
- Repo da co `.gitignore` cho cac pattern cookie/session pho bien, nhung ban van nen tu kiem tra truoc khi push

## Build EXE cho Windows

Tool da co script build san:

```powershell
.\scripts\build_exe.ps1
```

Script se:

- cai them dependency build neu can
- dung PyInstaller dong goi CLI
- tao file trong `dist\instaDow.exe`

Neu muon build voi ten khac:

```powershell
.\scripts\build_exe.ps1 -Name instaDowPro
```

## Goi y de ban tool gia 10$

- Ban source code + file `.exe` san dung cho Windows
- Kem file `README.md`, `targets.txt` mau, va huong dan export cookies
- Luu san config mac dinh de nguoi mua chi can thay `instagram_cookies.txt`
- Dung `--self-check` khi support khach tu xa, khong can hoi qua nhieu screenshot
- Goi san 2 mode ro rang trong mo ta san pham:
  `Profile mode`: tai feed + reels
  `Reels only mode`: chi tai reel tab

## Lenh goi y

Tai profile ca feed va reels:

```powershell
python -m instadow 11_14_42 --cookies-file .\instagram_cookies.txt
```

Chi tai reels:

```powershell
python -m instadow 11_14_42 --reels-only --cookies-file .\instagram_cookies.txt
```

Kiem tra metadata truoc:

```powershell
python -m instadow 11_14_42 --print-info --cookies-file .\instagram_cookies.txt -v
```
