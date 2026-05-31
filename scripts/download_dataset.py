import os
from modelscope.hub.snapshot_download import snapshot_download

def download_dataset_ms(dataset_id, local_dir):
    print(f"正在通过 ModelScope 准备下载数据集: {dataset_id}...")
    
    # 确保本地目录存在
    os.makedirs(local_dir, exist_ok=True)
    
    try:
        # 指定 repo_type 为 'dataset' 来拉取数据集仓库
        dataset_path = snapshot_download(
            dataset_id,
            repo_type="dataset",
            local_dir=local_dir
        )
        print(f"成功! {dataset_id} 已下载至: {dataset_path}\n")
    except Exception as e:
        print(f"下载 {dataset_id} 时发生错误: {e}\n")

if __name__ == "__main__":
    # 需要下载的数据集
    DATASETS_TO_DOWNLOAD = [
        "openfoodfacts/product-database",
        "openfoodfacts/open-prices"
    ]
    
    BASE_DOWNLOAD_DIR = "/home/yuki_noa/FoodAtlas/datasets_raw"
    
    for dataset_id in DATASETS_TO_DOWNLOAD:
        # 按照名称创建子文件夹
        folder_name = dataset_id.split("/")[-1]
        target_dir = os.path.join(BASE_DOWNLOAD_DIR, folder_name)
        
        download_dataset_ms(dataset_id, target_dir)