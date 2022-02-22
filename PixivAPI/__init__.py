from instance import *
import threading
from PixivApp import *
from PixivAPI import login_pixiv, HttpUtil, UrlConstant

Vars.cfg.load()
max_retry = Vars.cfg.data("headers", "retry")


def get(url: str) -> dict:
    return HttpUtil.get(url).json()


def image(url: str) -> bytes:
    return HttpUtil.get(url).content


class Download:

    @staticmethod
    def save_file(file_path: str, image_name: str, image_url: str):
        if not os.path.exists(os.path.join(file_path, f'{image_name}.png')):
            time.sleep(random.random() * float(1.2))  # 随机延迟
            with open(os.path.join(file_path, f'{image_name}.png'), 'wb+') as file:
                file.write(image(image_url))
                print('成功下载图片：{}\n'.format(image_name))
        else:
            print(f"{image_name} 已经下载过了\n")

    @staticmethod
    def save_image(image_id: str):
        file_path = Vars.cfg.data("user", "save_file")
        if "http" in image_id and len(image_id) > 20:
            image_name = image_id.split("/")[-1].replace(".jpg", "")
            Download.save_file(file_path, image_name, image_id)
        else:
            image_url, image_name = PixivApp.illustration_information(image_id)
            if type(image_url) is str:
                Download.save_file(file_path, image_name, image_url)
                return
            for index, url in enumerate(image_url):
                Download.save_file(file_path, image_name + f'_{index}', url)

    @staticmethod
    def threading_download(image_id_list: list):
        lock_tasks_list = threading.Lock()
        print(f"开始下载，一共 {len(image_id_list)} 张图片")

        def downloader():
            """多线程下载函数"""
            nonlocal lock_tasks_list

            while image_id_list:
                if not image_id_list and len(image_id_list) == 0:
                    return
                lock_tasks_list.acquire()
                image_id = image_id_list.pop(0) if image_id_list else False
                lock_tasks_list.release()
                if type(image_id) is not bool:
                    Download.save_image(str(image_id))

        threads_pool = []
        for _ in range(int(Vars.cfg.data("user", "max_thread"))):
            th = threading.Thread(target=downloader)
            threads_pool.append(th)
            th.start()

        # wait downloader
        for th in threads_pool:
            th.join()


class PixivToken:
    @staticmethod
    def instantiation_api():
        instantiation = AppPixivAPI()
        for index, retry in enumerate(range(int(max_retry))):
            instantiation.set_auth(
                access_token=Vars.cfg.data("user", "access_token"),
                refresh_token=Vars.cfg.data("user", "refresh_token")
            )
            if instantiation.illust_recommended().error is None:
                return instantiation

            login_pixiv.refresh(Vars.cfg.data("user", "refresh_token"))
            print(f"token失效，尝试刷新refresh_token retry{index}")
            if retry >= int(max_retry) - 1:
                return 403


class PixivApp:

    @staticmethod
    def illustration_information(works_id: int):
        """插画信息 <class 'PixivApp.utils.JsonDict'>"""
        response = get(UrlConstant.IMAGE_INFORMATION.format(works_id))
        information = response["illust"]
        image_name = information['title']
        page_count = information['page_count']

        tags_list = [
            data['translated_name'] for data in information['tags'] if data['translated_name']
        ]
        print("插画名称: {}:".format(image_name))
        print("插画ID: {}".format(information["id"]))
        print("作者ID: {}".format(information['user']["id"]))
        print("作者名称: {}".format(information['user']["name"]))
        print("插画标签: {}".format(', '.join(tags_list)))
        print("画集数量: {}".format(page_count))
        print("发布时间: {}\n".format(information["create_date"]))
        if page_count == 1:
            return information['meta_single_page']['original_image_url'], image_name
        img_url_list = [url['image_urls'].get("original") for url in information['meta_pages']]
        return img_url_list, image_name

    @staticmethod
    def start_information():
        """收藏插画 <class 'PixivApp.utils.JsonDict'>"""
        response = PixivToken.instantiation_api().illust_recommended()
        if response.error is None:
            image_id_list = list(set([data.id for data in response.illusts]))
            if type(image_id_list) is list and len(image_id_list) != 0:
                Download.threading_download(image_id_list)
        else:
            print(response.error)

    @staticmethod
    def recommend_information():
        """推荐插画 <class 'PixivApp.utils.JsonDict'>"""
        pixiv_app_api = PixivToken.instantiation_api()
        response = pixiv_app_api.illust_recommended()
        next_qs = pixiv_app_api.parse_qs(response.next_url)
        while next_qs is not None:
            if pixiv_app_api == 403:
                return "token invalid"
            response = pixiv_app_api.illust_recommended(**next_qs)
            if response.error is not None:
                return response.error
            image_id_list = list(set([data.id for data in response.illusts]))
            if type(image_id_list) is list and len(image_id_list) != 0:
                Download.threading_download(image_id_list)
            else:
                print("Pixiv推荐插图下载完毕")

    @staticmethod
    def follow_information():
        """关注用户信息 <class 'PixivApp.utils.JsonDict'>"""
        response = PixivToken.instantiation_api().illust_follow()
        if response.error is None:
            return list(set([data.id for data in response.illusts]))
        return response.error

    @staticmethod
    def author_information(author_id: str):
        """作者作品集 <class 'PixivApp.utils.JsonDict'>"""
        image_list = [UrlConstant.AUTHOR_INFORMATION.format(author_id, page) for page in range(1, 20)]
        for page, image_urL in enumerate(image_list):
            response = get(image_urL)
            if response.get("error") is not None:
                print(f"作者作品集下载完成，一共{page}页")
                return
            works_id_list = [data.get("id") for data in response.get("illusts")]
            Download.threading_download(works_id_list)


    @staticmethod
    def search_information(png_name: str, search_target: str):
        """搜索插画 <class 'PixivApp.utils.JsonDict'>"""
        response = PixivToken.instantiation_api().search_illust(
            word=png_name, search_target=search_target
        )
        if response.error is not None:
            return response.error
        original_urls_list = [
            url["image_urls"]["original"] for url in response.illusts[0].meta_pages
        ]

        if type(original_urls_list) is list and len(original_urls_list) != 0:
            Download.threading_download(original_urls_list)
