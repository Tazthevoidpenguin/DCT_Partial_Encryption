from pipeline import PipelineConfig, PipelineRun
from encryption import EncryptConfig
from getpass import getpass
from pathlib import Path


def input_int(print_mh: str, default: int, min_v: int, max_v: int) -> int:
    while True:
        val = input(print_mh).strip()
        if val == "":
            return default
        try:
            val = int(val)
        except ValueError:
            print("Gia tri phai la so nguyen, vui long nhap lai.")
            continue
        if min_v <= val <= max_v:
            return val
        print(f"Gia tri phai nam trong khoang {min_v}-{max_v}.")

def main():
    while True:
        choice=input_int("Nhap lua chon cua ban:\n1. Ma hoa anh\n2. Giai ma anh\n3. Thoat (Mac dinh la 3)\n",3,1,3)
        if(choice==1):
            input_path=input("Nhap duong dan anh:").strip()
            input_file = Path(input_path)
            while not input_file.is_file():
                print("Khong tim thay file anh, vui long nhap lai.")
                input_path=input("Nhap duong dan anh:").strip()
                input_file = Path(input_path)

            main_dir = Path(__file__).resolve().parent
            output_dir = main_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_suffix = input_file.suffix or ".png"
            output_path = output_dir / f"{input_file.stem}_encoded{output_suffix}"
            output_base = str(output_path)
            print(f"Anh ma hoa se duoc luu tai: {output_path}")
            #doan nay vibe chut de lay output chu toi ko biet lam =)))

            key_str = input("Nhap key cua ban (Mac dinh la Taz):").strip() or "Taz"
            #key_str = getpass("Nhap key cua ban (Mac dinh la Taz):").strip() or "Taz"
            key=key_str.encode("utf-8")

            key_id= input("Nhap key id:").strip()
            while key_id == "":
                print("Key id khong duoc de trong.")
                key_id= input("Nhap key id:").strip()

            valid_modes = ("ac_sign", "dc_bitplane", "hybrid", "stegno")
            inp_mode=input("Nhap mode (ac_sign/dc_bitplane/hybrid/stegno, mac dinh la hybrid):").strip() or "hybrid"
            while inp_mode not in valid_modes:
                print("Mode khong hop le.")
                inp_mode=input("Nhap mode (ac_sign/dc_bitplane/hybrid, mac dinh la hybrid):").strip() or "hybrid"

            inp_ac_cnt=input_int("Nhap so AC muon ma hoa (0-63, mac dinh la 5):",5,0,63)
            inp_dc_bitwidth=input_int("Nhap do rong bit cua DC (1-31, mac dinh la 7):",7,1,31)
            inp_dc_plane=input_int(
                f"Nhap so DC bitplane muon chia (0-{inp_dc_bitwidth}, mac dinh la 7):", min(7, inp_dc_bitwidth), 0, inp_dc_bitwidth,
            )
            mask_mode=input_int("Nhap kieu chon ma hoa (1. Toan bo/2. Trung tam/3. Xen ke/4. Ngau nhien), mac dinh la 1: ",1,1,4)
            valid_channels = ("Y", "Cb", "Cr")
            while True:
                inp_channels_str = input("Nhap cac kenh muon ma hoa (Y/Cb/Cr, cach nhau boi mot dau phay khong cach, mac dinh la Y):").strip()
                if inp_channels_str == "":
                    inp_channels = ("Y",)
                else:
                    inp_channels = tuple(
                        channel.strip()
                        for channel in inp_channels_str.split(",")
                        if channel.strip() != ""
                    )
                if (
                    inp_channels
                    and all(channel in valid_channels for channel in inp_channels)
                    and len(set(inp_channels)) == len(inp_channels)
                ):
                    break
                print("Kenh khong hop le hoac bi lap. Vi du hop le: Y,Cb.")
            #doan nay phai nho AI code =)))

            encrypt_config= EncryptConfig(
                mode=inp_mode,
                ac_count=inp_ac_cnt,
                dc_bitplanes=inp_dc_plane,
                dc_bit_width=inp_dc_bitwidth,
                channels=inp_channels,
            )
            inp_quality = input_int("Nhap chat luong anh (1-100, mac dinh la 75):",75,1,100)
            pipeline_config = PipelineConfig(
                quality=inp_quality,
                encryp= encrypt_config,
            )

            runner = PipelineRun(pipeline_config)
            runner.encode(input_path,output_base,key,key_id,mask_mode)


        elif(choice==2):
            input_path=input("Nhap duong dan anh da ma hoa:").strip()
            input_file = Path(input_path)
            metadata_path = input_file.with_suffix(".json")
            payload_path = input_file.with_suffix(".payload.npz")

            while not (input_file.is_file() and metadata_path.is_file() and payload_path.is_file()):
                print("Khong tim thay anh ma hoa, file JSON hoac file payload, vui long nhap lai.")
                input_path=input("Nhap duong dan anh da ma hoa:").strip()
                input_file = Path(input_path)
                metadata_path = input_file.with_suffix(".json")
                payload_path = input_file.with_suffix(".payload.npz")

            key_str = input("Nhap key cua ban (Mac dinh la Taz):").strip() or "Taz"
            key=key_str.encode("utf-8")

            main_dir = Path(__file__).resolve().parent
            output_dir = main_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            output_stem = input_file.stem
            if output_stem.endswith("_encoded"):
                output_stem = output_stem[:-len("_encoded")]
            decoded_path = output_dir / f"{output_stem}_decoded.png"

            runner = PipelineRun(PipelineConfig())
            runner.decode(input_path,str(decoded_path),key)
            print(f"Anh giai ma duoc luu tai: {decoded_path}")
            
        
        else:
            print("Git gud")
            break


if __name__ == "__main__":
    main()
