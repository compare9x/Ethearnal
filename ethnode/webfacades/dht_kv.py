from webfacades.webbase import WebApiBase
from kadem.kad import DHTFacade
from apifacades.dhtkv import DhtKv
from toolkit.filestore import FileSystemHashStore
import json
import cherrypy
import config
import requests
from toolkit import kadmini_codec as cdx


class WebDhtCdnInfo(WebApiBase):
    def __init__(self,
                 dkv: DhtKv,
                 cherry=None,
                 mount_point='/api/cdn/v1/info',
                 mount_it=True):
        super(WebDhtCdnInfo, self).__init__(
            cherry=cherry,
            mount_point=mount_point,
            mount_it=mount_it
        )
        self.dkv = dkv

    def GET(self, *a, **kw):
        self.cherry.response.headers["Access-Control-Allow-Origin"] = "*"
        # bad
        if 'known' in kw:
            ll = list()
            for guid in self.dkv.dhf.known_guids():
                data = self.dkv.get('cdn_info', guid_hex=guid, local=False)
                if data:
                    ll.append(data)
            if ll:
                js = json.dumps(ll, ensure_ascii=False)
                bs = js.encode()
                return bs
        data = self.dkv.get('cdn_info')
        js = json.dumps(data, ensure_ascii=False)
        bn = js.encode()
        return bn

    def OPTIONS(self):
        self.cherry.response.headers['Access-Control-Allow-Methods'] = 'GET POST HEAD OPTIONS'
        # self.cherry.response.headers['Access-Control-Allow-Headers'] = 'content-type Content-Type'
        allow = "Accept, Accept-Encoding, Content-Length, Content-Type, X-CSRF-Token"
        self.cherry.response.headers["Access-Control-Allow-Headers"] = allow
        self.cherry.response.headers["Access-Control-Expose-Headers"] = allow
        self.cherry.response.headers['Access-Control-Allow-Origin'] = '*'
        return b''


class WebDhtCdnSelector(WebApiBase):
    K_SELECTED_CDN = 'selected_cdn'

    def __init__(self,
                 dkv: DhtKv,
                 cherry=cherrypy,
                 mount_point='/api/v1/dht/cdn',
                 mount_it=True):
        super(WebDhtCdnSelector, self).__init__(
            cherry=cherry,
            mount_point=mount_point,
            mount_it=mount_it
        )
        self.dkv = dkv

    def GET(self, *a, **kw):
        data = self.dkv.get(self.K_SELECTED_CDN, local=True)
        js = json.dumps(data)
        bs = js.encode()
        return bs

    def PUT(self):
        return self.post()
        pass

    def post(self):
        body = self.cherry.request.body.read()
        data = json.loads(body.decode())
        # todo validate, sanitize
        self.dkv.set(self.K_SELECTED_CDN, data)
        return b''


class WebDhtCdnList(WebApiBase):
    K_OWN_CDN_LIST = 'cdn_list'

    def __init__(self,
                 dkv: DhtKv,
                 cherry=cherrypy,
                 cdn_list=None,
                 enable_cors=True,
                 mount_point='/api/v1/dht/cdn-list',
                 mount_it=True):
        super(WebDhtCdnList, self).__init__(
            cherry=cherry,
            mount_point=mount_point,
            mount_it=mount_it
        )
        self.cdn_list = cdn_list
        if not cdn_list:
            self.cdn_list = config.cdn_list
        self.dkv = dkv
        self.dkv.set(self.K_OWN_CDN_LIST, self.cdn_list)
        self.enable_cors = enable_cors,

    def GET(self, *a, **kw):
        if self.enable_cors:
            self.cherry.response.headers['Access-Control-Allow-Methods'] = 'POST GET'
            self.cherry.response.headers['Access-Control-Allow-Headers'] = 'content-type'
            self.cherry.response.headers['Access-Control-Allow-Origin'] = '*'
        data = self.dkv.get(self.K_OWN_CDN_LIST, local=True)
        js = json.dumps(data)
        bs = js.encode()
        return bs

    def PUT(self):
        if self.enable_cors:
            self.cherry.response.headers['Access-Control-Allow-Methods'] = 'POST GET'
            self.cherry.response.headers['Access-Control-Allow-Headers'] = 'content-type'
            self.cherry.response.headers['Access-Control-Allow-Origin'] = '*'
        return self.post()
        pass

    def post(self):
        body = self.cherry.request.body.read()
        data = json.loads(body.decode())
        # todo validate, sanitize
        self.dkv.set(self.K_OWN_CDN_LIST, data)
        return b''


class WebCdnClusterTrackerClient(object):
    def __init__(self, dhf: DHTFacade, http_host_port,
                 scheme='http:',
                 endpoint='/api/cdn/v1/track',
                 info_endpoint='/api/cdn/v1/info'):
        self.host_port = http_host_port
        self.scheme = scheme
        self.endpoint = endpoint
        self.info_endpoint = info_endpoint
        self.dhf = dhf

    @property
    def url(self):
        return self.url_st(self.scheme, self.host_port, self.endpoint)

    @staticmethod
    def url_st(scheme, host_port, endpoint) -> str:
        return '%s//%s%s' % (scheme, host_port, endpoint)

    def join(self, scheme=None, host_port=None, endpoint=None):
        # todo pass listen port now hardcoded to 5678 ( default cdn port)
        if not endpoint:
            endpoint = self.endpoint
        if not scheme:
            scheme = self.scheme
        if not host_port:
            host_port = self.host_port

        url = self.url_st(scheme, host_port, endpoint)

        print('JOIN TO: %s' % url)
        r = requests.put(url)
        if r.status_code == 200:
            return r.content.decode()

    def data(self, scheme=None, host_port=None, endpoint=None):
        if not endpoint:
            endpoint = self.endpoint
        if not scheme:
            scheme = self.scheme
        if not host_port:
            host_port = self.host_port
        url = self.url_st(scheme, host_port, endpoint)
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()

    def info_data(self, scheme=None, host_port=None, info_endpoint=None):
        if not info_endpoint:
            info_endpoint = self.info_endpoint
        if not scheme:
            scheme = self.scheme
        if not host_port:
            host_port = self.host_port
        url = self.url_st(scheme, host_port, info_endpoint)
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()

    def join_to_list(self, scheme=None, host_port=None, endpoint=None,
                     join_dht=True,
                     push_pub=True,
                     pull_pubs=True):

        data = self.data(scheme=scheme, host_port=host_port, endpoint=endpoint)
        if data:
            members = data.get("cluster_members")
            if members:
                for item_host_port in members:
                    self.join(scheme=scheme, host_port=item_host_port,  endpoint=endpoint)
                    if join_dht:
                        self.join_dht(host_port=item_host_port)
                        if push_pub:
                            self.dhf.push_pubkey()
        if pull_pubs:
            self.dhf.pull_pubkey_in_peers()

    def join_dht(self, scheme=None, host_port=None, info_endpoint=None):
        info_data = self.info_data(scheme=scheme, host_port=host_port, info_endpoint=info_endpoint)
        udp_data = info_data.get('udp')
        if udp_data:
            ip4 = udp_data.get('ip4')
            port = udp_data.get('port')
            if ip4 and port:
                print('BOOT TO', ip4, port)
                self.dhf.boot_to(ip4, port)


class WebCdnClusterTracker(WebApiBase):
    def __init__(self,
                 hfs: FileSystemHashStore,
                 http_srv_ip,
                 http_srv_port,
                 rcli: WebCdnClusterTrackerClient = None,
                 enable_cors=True,
                 cherry=cherrypy,
                 mount_point='/api/cdn/v1/track',
                 mount_it=True):

        super(WebCdnClusterTracker, self).__init__(
            cherry=cherry,
            mount_point=mount_point,
            mount_it=mount_it
        )
        self.ip = http_srv_ip
        self.port = http_srv_port
        self.rcli = rcli
        self.hfs = hfs
        self.enable_cors = enable_cors
        # truncate previous saved data
        self.hfs.save_bts_str_key('tracker', json.dumps({'cluster_members': []},
                                                        ensure_ascii=False).encode())

    def save_data(self, data, key='tracker'):
        js = json.dumps(data, ensure_ascii=False)
        self.hfs.save_bts_str_key(key, js.encode())

    def load_data(self, key='tracker', bin_only=False):
        bio = self.hfs.read_io(key)
        if not bio:
            return
        bin_data = bio.read()
        if bin_only:
            return bin_data
        txt_data = bin_data.decode()
        data = json.loads(txt_data)
        return data

    def join_cluster(self, host_port: str, headers: dict, join_back=False):
        tracker_data = self.load_data()
        ll = None
        if not tracker_data:
            tracker_data = dict()
            ll = list()
            tracker_data['cluster_members'] = ll
        elif 'cluster_members' in tracker_data:
            ll = tracker_data['cluster_members']
        else:
            ll = list()
            tracker_data['cluster_members'] = ll

        if host_port in ll:
            print('DEBUG: host_port %s there pass' % host_port)
            return host_port.encode()

        if host_port not in ll:
            ll.append(host_port)
        else:
            self.cherry.response.status = 409
            return b''

        self.save_data(tracker_data)
        msg = 'DEBUG: join to %s' % host_port

        print(msg)
        if join_back:
            if self.rcli:
                if "Remote-Addr" in headers:
                    client_ip4 = headers["Remote-Addr"]
                    if client_ip4 != self.ip:
                        # todo port
                        self.rcli.join(host_port='%s:5678' % client_ip4)
        return msg.encode()

    def get_tracker_data(self):
        return self.load_data(bin_only=True)

    def PUT(self):
        if self.enable_cors:
            self.cherry.response.headers['Access-Control-Allow-Methods'] = 'POST GET'
            self.cherry.response.headers['Access-Control-Allow-Headers'] = 'content-type'
            self.cherry.response.headers['Access-Control-Allow-Origin'] = '*'
        headers = self.cherry.request.headers
        host_port = 'null'
        if "Remote-Addr" in headers:
            # todo custom port
            host_port = '%s:%s' % (headers["Remote-Addr"], '5678')
            st = self.join_cluster(host_port, headers, join_back=True)
            return host_port.encode()
        return host_port

    def GET(self):
        if self.enable_cors:
            self.cherry.response.headers['Access-Control-Allow-Methods'] = 'POST GET'
            self.cherry.response.headers['Access-Control-Allow-Headers'] = 'content-type'
            self.cherry.response.headers['Access-Control-Allow-Origin'] = '*'
        return self.get_tracker_data()

from toolkit.thumb import ImgThumbnail
import os
import io
import bson


class WebCdnResourceApiClient(object):
    def __init__(self, dhf: DHTFacade, http_host_port,
                 scheme='http:',
                 endpoint='/api/cdn/v1/resource',
                 ):
        self.host_port = http_host_port
        self.scheme = scheme
        self.endpoint = endpoint
        self.dhf = dhf

    @property
    def url(self):
        return self.url_st(self.scheme, self.host_port, self.endpoint)

    @staticmethod
    def url_st(scheme, host_port, endpoint) -> str:
        return '%s//%s%s' % (scheme, host_port, endpoint)

    def upload(self, ufile):
        print('UPLOAD URL', self.url)
        return b''
        pass

    def download(self, hk_hex, thumb=False):
        url_q = '%s?hkey=%s' % (self.url, hk_hex)
        if thumb:
            url_q = '%s&thumb=1' % url_q
        print('RES CLI GET url %s' % url_q)
        r = requests.get(url_q)
        if r.status_code != 200:
            print('RESP CODE NOT OK: ->', r.status_code)
            return r
        else:
            return r


class WebCDNRefactorWebCdnResourceApi(WebApiBase):
    def __init__(self,
                 dhf=None,
                 enable_cors=True,
                 cherry=cherrypy,
                 mount_point: str = '/api/cdn/v1/resource',
                 store_dir: str='cdn_profile/',
                 mount_it=True):

        super(WebCDNRefactorWebCdnResourceApi, self).__init__(
            cherry=cherry,
            mount_point=mount_point,
            mount_it=mount_it
        )

        self.cherry = cherry
        self.mount_point = mount_point
        self.store_dir = os.path.abspath(store_dir)
        self.dhf = dhf
        self.dhf.cdn = self
        self.enable_cors = True
        self.thumbnail = ImgThumbnail()

        if mount_it:
            self.mount()
            print('MOUNT WEB:', self.mount_point)

    def get_local_meta_data(self, hkey):
        f_name_meta = '%s.%s' % (hkey, 'json')
        upload_file_meta = os.path.join(self.store_dir, f_name_meta)
        data_d = None
        if not os.path.isfile(upload_file_meta):
            self.cherry.response.status = 410
            return data_d
        with open(upload_file_meta, 'rb') as u_f_m:
            data = u_f_m.read()
            data_d = json.loads(data.decode())
        u_f_m.close()
        return data_d

    def get_local_data(self, hkey, fext):
        try:
            f_name = '%s.%s' % (hkey, fext)
            #  upload_path = os.path.join(self.store_dir)
            upload_file = os.path.join(self.store_dir, f_name)
        except Exception as e:
            msg = '{"error":"general error with getting file name %s"}' % str(e)
            self.cherry.response.status = 410
            print(msg)
            return None

        if not os.path.isfile(upload_file):
            self.cherry.response.status = 411
            msg = '{"error":"% s not found" }' % upload_file
            print(msg)
            return None

        size = 0
        uf = io.BytesIO()
        try:
            with open(upload_file, 'rb') as u_f:
                while True:
                    data = u_f.read(8192)
                    if not data:
                        break
                    uf.write(data)
                    size += len(data)
            u_f.close()
            uf.seek(0)
            bts = uf.read()
            return bts
        except:
            return None

    def get_remote_meta_data(self, cdn_url, hkey):

        url = '%s?hkey=%s&meta=1' % (cdn_url, hkey)

        return self.get_file_from_url(url)

    def get_remote_data(self, cdn_url, hkey):
        # self.cherry.response.headers['Relay-Id-Source'] = '%s:%d' % (self.dhf.ert.cdn_host, self.dhf.ert.cdn_port)
        print('GET REMOTE DATA')
        url = '%s?hkey=%s' % (cdn_url, hkey)
        print('GET URL', url)
        return self.get_file_from_url(url)

    def set_local_meta_data(self, hkey, data):
        # self.cherry.response.headers['Relay-Id-Source'] = '%s:%d' % (self.dhf.ert.cdn_host, self.dhf.ert.cdn_port)
        f_name_meta = '%s.%s' % (hkey, 'json')
        upload_file_meta = os.path.join(self.store_dir, f_name_meta)
        data_js = json.dumps(data, ensure_ascii=False)
        data_bt = data_js.encode()
        with open(upload_file_meta, 'wb') as u_f_m:
            u_f_m.write(data_bt)
        u_f_m.close()

    def set_local_data(self, hkey, fext, bts):
        f_name = '%s.%s' % (hkey, fext)

        upload_file = os.path.join(self.store_dir, f_name)
        with open(upload_file, 'wb') as oufp:
            oufp.write(bts)
        oufp.close()

    # @staticmethod
    def get_file_from_url(self, url):
        print('GET RELAY META', url)
        try:
            relay_header_key = 'Relay-Id-Source'
            print(self.dhf.ert.cdn_host, self.dhf.ert.cdn_port)
            relay_header_val = '%s:%d' % (self.dhf.ert.cdn_host, self.dhf.ert.cdn_port)
            print('GET RELAY HEADER', relay_header_key, relay_header_val)

            r = requests.get(url, headers={relay_header_key: relay_header_val}, stream=True)
            print('RELAY RESP CODE', r.status_code)
            # print('RELAY RESP CONTENT', r.content.decode())
            # fpio = io.BytesIO()
            print('GET FROM URLK', r, r.status_code)
            if r.status_code == 200:
                r.raw.decode_content = True
                bts = r.raw.read()
                print('BTS', len(bts))
                # print(')
                return bts
            else:
                return None
        except Exception as e:
            print('ERR e',e)
            return None

    # def dhf_pull(self, hk_hex):
    #     t1 = self.dhf.pull_local('', hk_hex=hk_hex)
    #     t2 = self.dhf.pull_remote('', hk_hex=hk_hex)
    #     if t2:
    #         t = t2
    #     else:
    #         t = t1
    #     if not t:
    #         return None
    #     d = bson.loads(t[-1])
    #     return d

    # @property
    # def cdn_url(self):
    #     return '%s%s' % (self.dhf.ert.cdn_service_http_url, self.mount_point)
    #
    # def on_post(self, hk_hex):
    #     self.dhf.push('', {'cdn_url': self.cdn_url,
    #                        'hk_hex': hk_hex,
    #                        }, hk_hex=hk_hex, remote_only=False)

    # def try_get_meta(self, hkey):
    #
    #     print('TRY GET META:', hkey)
    #     try:
    #         t = self.dhf.pull_remote(key='', hk_hex=hkey)
    #
    #         if not t:
    #             return
    #         v = bson.loads(t[-1])
    #         print('META V', v)
    #         if 'e' in v:
    #             l = v['e']
    #             d = l[1]
    #             if 'cdn_url' in d:
    #                 url = d['cdn_url']
    #                 if '127.0.0.1' in url:
    #                     print('LOOPBACK DETECTED IGNORE')
    #                     return None
    #                 bts = self.get_remote_meta_data(cdn_url=url, hkey=hkey)
    #                 meta_dict = json.loads(bts.decode())
    #                 self.set_local_meta_data(hkey, data=meta_dict)
    #                 print('METADATA SAVED')
    #                 # return meta_dict
    #                 return url
    #
    #         # print('ON GET ', d)
    #     except Exception as e:
    #         print('e e e ', str(e))
    #     # print("T", t, len(t))

    def read_from_file_response(self, fn):
        size = 0
        uf = io.BytesIO()
        try:
            with open(fn, 'rb') as u_f:
                while True:
                    data = u_f.read(8192)
                    if not data:
                        break
                    uf.write(data)
                    size += len(data)
            u_f.close()
            uf.seek(0)
            bts = uf.read()
            self.cherry.response.status = 200
            return bts
        except Exception as e:
            self.cherry.response.status = 400
            err = '{"error with thumb":"%s"}' % str(e)
            return err.encode()

    def GET(self, hkey=None, relay_id=None, thumb=None, meta=None):
        if self.enable_cors:
            self.set_cors_headers()

        request_headers = self.cherry.request.headers
        def invalid_hkey(cherry):
            cherry.response.status = 401
            return b'{"error":"invalid hkey"}'

        if not hkey:
            return invalid_hkey(self.cherry)
        if len(hkey) != 64:
            return invalid_hkey(self.cherry)

        try:
            f_name_meta = '%s.%s' % (hkey, 'json')
            upload_file_meta = os.path.join(self.store_dir, f_name_meta)
        except:
            self.cherry.response.status = 400
            return b'{"error":"can\'t construct meta_file"}'

        try:
            if not os.path.isfile(upload_file_meta):
                print('META-FILE NOT FOUND')
                self.cherry.response.status = 400
                return b'{"error":"metafile missing"}'

            with open(upload_file_meta, 'rb') as u_f_m:
                data = u_f_m.read()
                if meta:
                    return data
                    # only metadata requested
                data_d = json.loads(data.decode())
                fext = data_d['fext'].strip()
                hk_meta = data_d['hkey'].strip()
                ct = data_d["Content-Type"].strip()
                cherrypy.response.headers["Content-Type"] = ct
                if hkey != hk_meta or not fext or not ct:
                    return b'{"error":"integrity error with hkey diff metadata"}'

        except OSError as e:
            self.cherry.response.status = 400
            msg = '{"error":"resource missing"}'
            return msg.encode()

        except Exception as e:
            msg = '{"error":"exc %s}' % str(e)
            self.cherry.response.status = 400
            return msg.encode()

        if not fext:
            self.cherry.response.status = 400
            return b'{"error":"unknown file extension"}'

        try:
            f_name = '%s.%s' % (hkey, fext)
            upload_file = os.path.join(self.store_dir, f_name)
        except OSError as e:
            self.cherry.response.status = 401
            msg = '{"error":"os path join %s %s"}' % (str(hkey), str(fext))
            return msg.encode()
        except Exception as e:
            self.cherry.response.status = 401
            msg = '{"error":"general error with getting file name %s"}' % str(e)
            return msg.encode()

        if not os.path.isfile(upload_file):
            self.cherry.response.status = 400
            return b'{"error":"Data file missing"}'

        if thumb:
            thumb_name = self.thumbnail.get_file_name(upload_file)
            if 'svg' in thumb_name:
                return self.read_from_file_response(upload_file)
            if not os.path.isfile(thumb_name):
                self.thumbnail.resize(upload_file, 400, 400)
            return self.read_from_file_response(self.thumbnail.get_file_name(upload_file))
        else:
            return self.read_from_file_response(upload_file)

    def POST(self, ufile):
        if self.enable_cors:
            self.set_cors_headers()
        ct = None
        try:
            ct = str(ufile.content_type)
            fext = ct.split('/')[1]
            if not ct:
                self.cherry.response.status = 408
                return b'{"error":"can\'t determine content-type"}'
        except:
            self.cherry.response.status = 408
            return b'{"error":"can\'t determine content-type"}'
        size = 0
        uf = io.BytesIO()
        while True:
            data = ufile.file.read(8192)
            if not data:
                break
            uf.write(data)
            size += len(data)

        uf.seek(0)
        uf_bts = uf.read()
        hk = cdx.guid_bin_to_hex(cdx.sha256_bin_digest(uf_bts))
        st_hk = hk.decode()
        f_name = '%s.%s' % (st_hk, fext)
        f_name_meta = '%s.json' % st_hk
        upload_file = os.path.join(self.store_dir, f_name)
        upload_meta_file = os.path.join(self.store_dir, f_name_meta)

        with open(upload_file, 'wb') as u_f:
            uf.seek(0)
            u_f.write(uf.read())
        u_f.close()
        # resize for thumbnails

        try:
            self.thumbnail.resize(fn=upload_file, max_w=400, max_h=400)
        except Exception as e:
            print('WARNING THUMBNAIL FAILED', e)

        with open(upload_meta_file, 'wb') as u_m_f:
            u_m_f.write(json.dumps({'fext': fext, 'hkey': st_hk, "Content-Type": ct}, ensure_ascii=False).encode())
        u_m_f.close()
        # self.on_post(st_hk)

        self.cherry.response.status = 201
        return hk.decode()

    def on_post(self, hk_hex):
        print("ON_POST RES:", hk_hex)
        return

    def push_resource(self, hk_hex):
        # 'TEST'
        cdn = 'URL4: %s' % hk_hex
        self.dhf.push(key='', value={'cdn': cdn,
                                     'hk_hex': hk_hex,
                                     }, hk_hex=hk_hex, local_only=True)

    def pull_resource(self, hk_hex, remote=True):
        if remote:
            t = self.dhf.pull_remote(key='', hk_hex=hk_hex)
        else:
            t = self.dhf.pull_local(key='', hk_hex=hk_hex)
        print('pull t', t)
        if t:
            v = cdx.value_protocol_ert(t)
            if v:
                return v

    def OPTIONS(self):
        if self.enable_cors:
            self.set_cors_headers()
        # cherrypy.response.headers['Access-Control-Allow-Methods'] = 'POST GET'
        # cherrypy.response.headers['Access-Control-Allow-Headers'] = 'content-type'
        # cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        # tell CherryPy no avoid normal handler
        return b''


