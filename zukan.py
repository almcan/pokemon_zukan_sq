import requests
import os
import time
import re 

# --- 設定項目 ---
BASE_API_URL = "https://zukan.pokemon.co.jp/zukan-api/api/search/"
IMAGE_KEY = 'image_s'
SAVE_DIRECTORY = "pokemon_images"
API_REQUEST_DELAY = 0.5
IMAGE_DOWNLOAD_DELAY = 0.1
# --- 設定項目ここまで ---

# 名前や図鑑番号も一緒に保存するリスト
pokemon_image_data = [] 

pokemon_per_page = 64
total_pages = 0

# --- ステップ1: APIから画像URLと関連情報 (図鑑番号、名前) を取得 ---
print("--- ステップ1: ポケモン情報 (図鑑番号, 名前, 画像URL) の取得開始 ---")

try:
    print(f"ページ 1 を取得中 (総ページ数確認のため)...")
    params = {'limit': pokemon_per_page, 'page': 1}
    response = requests.get(BASE_API_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    paging_info = data.get("paging", {})
    total_pages = paging_info.get("pageCount", 0)
    
    if total_pages == 0:
        print("エラー: APIレスポンスから総ページ数を特定できませんでした。")
        print(f"デバッグ情報 (paging): {paging_info}")
        exit()
        
    print(f"総ページ数: {total_pages}")

    # 最初のページから情報を収集
    current_page_items = 0
    for pokemon in data.get("results", []):
        # 画像URL、図鑑番号、名前が存在するか確認
        img_url = pokemon.get(IMAGE_KEY)
        zukan_no = pokemon.get("zukan_no")
        name = pokemon.get("name")
        if img_url and zukan_no and name:
            pokemon_image_data.append({
                "no": zukan_no,
                "name": name,
                "url": img_url
            })
            current_page_items += 1
    # print(f"ページ 1 から {current_page_items} 件のポケモン情報を取得しました。")
    
    time.sleep(API_REQUEST_DELAY)

except requests.exceptions.RequestException as e:
    print(f"エラー: ページ 1 の取得に失敗しました。理由: {e}")
    exit()
except ValueError:
    print(f"エラー: ページ 1 のJSONデータの解析に失敗しました。レスポンス内容 (先頭200文字): {response.text[:200]}...")
    exit()

# 2ページ目から残りのページを取得
if total_pages > 1:
    for page_num in range(2, total_pages + 1):
        # print(f"ページ {page_num}/{total_pages} を取得中...")
        params = {'limit': pokemon_per_page, 'page': page_num}
        try:
            response = requests.get(BASE_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            current_page_items = 0
            for pokemon in data.get("results", []):
                img_url = pokemon.get(IMAGE_KEY)
                zukan_no = pokemon.get("zukan_no")
                name = pokemon.get("name")
                if img_url and zukan_no and name:
                    pokemon_image_data.append({
                        "no": zukan_no,
                        "name": name,
                        "url": img_url
                    })
                    current_page_items += 1
            # print(f"ページ {page_num} から {current_page_items} 件のポケモン情報を取得しました。")
            
            time.sleep(API_REQUEST_DELAY)

        except requests.exceptions.RequestException as e:
            print(f"エラー: ページ {page_num} の取得に失敗しました。理由: {e}")
            print("このページをスキップして次に進みます。")
            continue
        except ValueError:
            print(f"エラー: ページ {page_num} のJSONデータの解析に失敗しました。レスポンス内容 (先頭200文字): {response.text[:200]}...")
            print("このページをスキップして次に進みます。")
            continue

print(f"--- ポケモン情報の取得完了 ---")
print(f"合計 {len(pokemon_image_data)} 件の情報を取得しました。")


# --- ステップ2: 取得した情報から画像をダウンロードしてポケモン名で保存 ---
if not pokemon_image_data:
    print("ポケモン情報が取得できなかったため、ダウンロード処理をスキップします。")
else:
    print(f"\n--- ステップ2: {len(pokemon_image_data)} 個の画像のダウンロード開始 ---")
    
    if not os.path.exists(SAVE_DIRECTORY):
        try:
            os.makedirs(SAVE_DIRECTORY)
            print(f"フォルダ '{SAVE_DIRECTORY}' を作成しました。")
        except OSError as e:
            print(f"エラー: フォルダ '{SAVE_DIRECTORY}' の作成に失敗しました。理由: {e}")
            print("ダウンロード処理を中断します。")
            exit()

    successful_downloads = 0
    failed_downloads = 0
    
    # ファイル名に使えない文字を置換するための関数
    def sanitize_filename(name):
        # Windows/Mac/Linuxで共通して問題になりそうな文字を置換 (例: _ に置換)
        # 必要に応じて他の文字 (\, *, ?, ", <, >, | など) も追加してください
        name = re.sub(r'[\\/:?*"<>|]+', '_', name)
        # ファイル名の先頭や末尾のスペースも除去
        return name.strip()

    for i, item in enumerate(pokemon_image_data):
        img_url = item['url']
        zukan_no = item['no']
        pokemon_name = item['name']
        
        try:
            # ファイル名を作成 (例: 0001_フシギダネ.png)
            
            # 元のURLから拡張子を取得 (例: .png)
            # URLの末尾にパラメータ(?...)が付いている場合も考慮
            url_path = img_url.split('?')[0] # パラメータを除去
            if '.' in url_path.split('/')[-1]:
                extension = '.' + url_path.split('.')[-1]
            else:
                extension = '.png' # 拡張子が不明な場合は .png とする (仮)
                
            # ポケモン名をファイル名として安全な形に処理
            safe_pokemon_name = sanitize_filename(pokemon_name)
            
            # 図鑑番号と名前を組み合わせたファイル名
            filename = f"{zukan_no}_{safe_pokemon_name}{extension}"
            
            save_path = os.path.join(SAVE_DIRECTORY, filename)
            
            # print(f"({i+1}/{len(pokemon_image_data)}) ダウンロード中: {pokemon_name} ({zukan_no}) -> {save_path}")
            
            img_response = requests.get(img_url, stream=True, timeout=20)
            img_response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in img_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            successful_downloads += 1
            
            time.sleep(IMAGE_DOWNLOAD_DELAY)

        except requests.exceptions.RequestException as e:
            print(f"エラー: {pokemon_name} ({img_url}) のダウンロードに失敗しました。理由: {e}")
            failed_downloads += 1
        except Exception as e:
            print(f"予期せぬエラー ({pokemon_name}, {img_url}): {e}")
            failed_downloads += 1

    print("\n--- 画像のダウンロード処理完了 ---")
    print(f"成功: {successful_downloads} 件")
    print(f"失敗: {failed_downloads} 件")
    if failed_downloads > 0:
        print("一部の画像のダウンロードに失敗しました。エラーメッセージを確認してください。")