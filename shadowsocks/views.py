# 导入django内置模块
from django.shortcuts import render, render_to_response, redirect, HttpResponseRedirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.six import BytesIO
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic.list import ListView
from django.db.models import Q
# 导入shadowsocks节点相关文件
from .models import Node, InviteCode, User, Aliveip, Donate, Shop, MoneyCode, PurchaseHistory, AlipayRecord
from .forms import RegisterForm, LoginForm, NodeForm, ShopForm

# 导入ssservermodel
from ssserver.models import SSUser

# 导入第三方模块
import qrcode
import base64
import datetime
from random import randint


# Create your views here.

# 网站用户界面：

def index(request):
    '''跳转到首页'''
    return render_to_response('sspanel/index.html')


def sshelp(request):
    '''跳转到帮助界面'''
    return render_to_response('sspanel/help.html')


def ssclient(request):
    '''跳转到客户端界面'''
    return render_to_response('sspanel/client.html')


def ssinvite(request):
    '''跳转到邀请码界面'''
    codelist = InviteCode.objects.all()[:20]

    context = {'codelist': codelist, }

    return render(request, 'sspanel/invite.html', context=context)


def pass_invitecode(request, invitecode):
    '''提供点击邀请码连接之后自动填写邀请码'''
    form = RegisterForm(initial={'invitecode': invitecode})
    return render(request, 'sspanel/register.html', {'form': form})


def nodeinfo(request):
    '''跳转到节点信息的页面'''

    nodelists = []
    # 将节点信息查询结果保存dict中，方便增加在线人数字段
    nodes = Node.objects.values()
    ss_user = request.user.ss_user
    user = request.user
    Alive = Aliveip.objects.all()
    # 循环遍历没一条线路的在线人数
    for node in nodes:
        node['count'] = len(Alive.filter(node_id=node['node_id']))
        nodelists.append(node)

    context = {
        'nodelists': nodelists,
        'ss_user': ss_user,
        'user': user,
    }

    return render(request, 'sspanel/nodeinfo.html', context=context)


def register(request):
    '''用户注册时的函数'''
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            # 获取用户填写的邀请码
            code = request.POST.get('invitecode')
            # 数据库查询邀请码
            code_query = InviteCode.objects.filter(code=code)
            # 判断邀请码是否存在并返回信息
            if len(code_query) == 0:
                registerinfo = {
                    'title': '邀请码失效',
                    'subtitle': '请重新获取邀请码',
                    'status': 'error',
                }
                context = {
                    'registerinfo': registerinfo,
                    'form': form,
                }
                return render(request, 'sspanel/register.html', context=context)

            else:
                registerinfo = {
                    'title': '注册成功！',
                    'subtitle': '请登录使用吧！',
                    'status': 'success',
                }
                context = {
                    'registerinfo': registerinfo
                }
                form.save()
                # 删除使用过的邀请码
                code_query.delete()
                # 将user和ssuser关联
                user = User.objects.get(username=request.POST.get('username'))
                max_port_user = SSUser.objects.order_by('-port').first()
                port = max_port_user.port + randint(2, 3)
                ss_user = SSUser.objects.create(user=user, port=port)
                return render(request, 'sspanel/index.html', context=context)

    else:
        form = RegisterForm()

    return render(request, 'sspanel/register.html', {'form': form})


def Login_view(request):
    '''用户登录函数'''
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            # 获取表单用户名和密码
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # 进行用户验证
            user = authenticate(username=username, password=password)
            if user is not None and user.is_active:
                login(request, user)
                registerinfo = {
                    'title': '登录成功！',
                    'subtitle': '自动跳转到用户中心',
                    'status': 'success',
                }
                context = {
                    'registerinfo': registerinfo,
                }
                return render(request, 'sspanel/userinfo.html', context=context)
            else:
                form = LoginForm()
                registerinfo = {
                    'title': '登录失败！',
                    'subtitle': '请重新填写信息！',
                    'status': 'error',
                }
                context = {
                    'registerinfo': registerinfo,
                    'form': form,

                }
                return render(request, 'sspanel/login.html', context=context)
    else:
        form = LoginForm()
        return render(request, 'sspanel/login.html', {'form': form})


def Logout_view(request):
    '''用户登出函数'''
    logout(request)
    registerinfo = {
        'title': '注销成功！',
        'subtitle': '欢迎下次再来!！',
                    'status': 'success',
    }
    context = {
        'registerinfo': registerinfo,
    }

    return render(request, 'sspanel/index.html', context=context)


@login_required
def userinfo(request):
    '''用户中心'''
    user = request.user
    context = {
        'user': user,
    }

    return render(request, 'sspanel/userinfo.html', context=context)


@login_required
def checkin(request):
    '''用户签到'''
    ss_user = request.user.ss_user
    if timezone.now() - datetime.timedelta(days=1) > ss_user.last_check_in_time:
        # 距离上次签到时间大于一天 增加200m流量
        ss_user.transfer_enable += int(200 * 1024 * 1024)
        ss_user.last_check_in_time = timezone.now()
        ss_user.save()
        registerinfo = {
            'title': '签到成功！',
            'subtitle': '获得200m流量',
            'status': 'success', }
    else:
        registerinfo = {
            'title': '签到失败！',
            'subtitle': '距离上次签到不足一天',
            'status': 'error', }

    context = {
        'registerinfo': registerinfo,
        'ss_user': ss_user,
    }
    return render(request, 'sspanel/userinfo.html', context=context)


@login_required
def get_ss_qrcode(request, node_id):
    '''返回节点配置信息的二维码'''
    # 获取用户对象
    ss_user = request.user.ss_user
    # 获取节点对象
    node = Node.objects.get(node_id=node_id)

    ss_code = '{}:{}@{}:{}'.format(
        node.method, ss_user.password, node.server, ss_user.port)

    # 符合ssr qrcode schema最后需要特殊处理的密码部分
    ssr_password = base64.b64encode(
        bytes(ss_user.password, 'utf8')).decode('ascii')
    ssr_code = '{}:{}:{}:{}:{}:{}'.format(
        node.server, ss_user.port, node.protocol, node.method, node.obfs, ssr_password)
    # 将信息编码
    ss_pass = base64.b64encode(bytes(ss_code, 'utf8')).decode('ascii')
    ssr_pass = base64.b64encode(bytes(ssr_code, 'utf8')).decode('ascii')

    # 生成ss二维码
    ss_img = qrcode.make('ss://{}'.format(ss_pass))
    ssr_img = qrcode.make('ssr://{}'.format(ssr_pass))
    buf = BytesIO()
    ssr_img.save(buf)
    image_stream = buf.getvalue()
    # 构造图片reponse
    response = HttpResponse(image_stream, content_type="image/png")

    return response


@login_required
def userinfo_edit(request):
    '''跳转到资料编辑界面'''
    ss_user = request.user.ss_user
    context = {
        'ss_user': ss_user,
    }
    return render(request, 'sspanel/userinfoedit.html', context=context)


def donate(request):
    '''跳转到捐赠界面'''
    donatelist = Donate.objects.all()[:15]
    context = {'donatelist': donatelist, }
    # 尝试获取流水号
    if request.method == 'POST':
        info_code = request.POST.get('q')
        try:
            obj = AlipayRecord.objects.get(info_code=info_code)
            context['moneycode'] = obj.money_code
        except:
            registerinfo = {
                'title': '请确保流水号填写正确!',
                'subtitle': '如果一直失败,请通过支付联系站长',
                'status': 'error', }
            context['registerinfo'] = registerinfo
    else:
        pass

    return render(request, 'sspanel/donate.html', context=context)


def shop(request):
    '''跳转到商品界面'''
    ss_user = request.user

    goods = Shop.objects.all()

    context = {'ss_user': ss_user,
               'goods': goods, }

    return render(request, 'sspanel/shop.html', context=context)


def purchase(request, goods_id):
    '''商品购买逻辑'''

    goods = Shop.objects.all()
    good = goods.get(pk=goods_id)
    user = request.user
    ss_user = request.user.ss_user

    if user.balance < good.money:
        registerinfo = {
            'title': '金额不足！',
            'subtitle': '请联系站长充值',
            'status': 'error', }
        context = {'ss_user': ss_user,
                   'goods': goods,
                   'registerinfo': registerinfo,
                   }
        return render(request, 'sspanel/shop.html', context=context)

    else:
        # 验证成功进行提权操作
        ss_user.transfer_enable += good.transfer
        user.balance -= good.money
        user.level = good.level
        ss_user.save()
        user.save()
        # 增加购买记录
        record = PurchaseHistory(info=good, user=user,
                                 purchtime=timezone.now())
        record.save()
        registerinfo = {
            'title': '够买成功',
            'subtitle': '即将跳转回用户中心',
            'status': 'success', }

        context = {
            'ss_user': ss_user,
            'registerinfo': registerinfo,
        }
        return render(request, 'sspanel/userinfo.html', context=context)


def chargecenter(request):
    '''充值界面的跳转'''
    user = request.user
    codelist = MoneyCode.objects.filter(user=user)

    context = {'ss_user': user,
               'codelist': codelist}

    return render(request, 'sspanel/chargecenter.html', context=context)


def charge(request):
    user = request.user
    if request.method == 'POST':
        input_code = request.POST.get('chargecode')
        # 在数据库里检索充值
        code_query = MoneyCode.objects.filter(code=input_code)
        # 判断充值码是否存在
        if len(code_query) == 0:
            registerinfo = {
                'title': '充值码失效',
                'subtitle': '请重新获取充值码',
                'status': 'error',
            }
            context = {
                'registerinfo': registerinfo,
                'ss_user': user,
            }
            return render(request, 'sspanel/chargecenter.html', context=context)

        else:
            code = code_query[0]
            # 判断充值码是否被使用
            if code.isused == True:
                # 当被使用的是时候
                registerinfo = {
                    'title': '充值码失效',
                    'subtitle': '请重新获取充值码',
                    'status': 'error', }
                context = {
                    'registerinfo': registerinfo,
                    'ss_user': user, }
                return render(request, 'sspanel/chargecenter.html', context=context)
            else:
                # 充值操作
                user.balance += code.number
                code.user = user.username
                code.isused = True
                user.save()
                code.save()
                # 将充值记录和捐赠绑定
                donate = Donate.objects.create(user=user, money=code.number)
                registerinfo = {
                    'title': '充值成功！',
                    'subtitle': '请去商店购买商品！',
                    'status': 'success',
                }
                context = {
                    'registerinfo': registerinfo,
                    'ss_user': user,
                }
                return render(request, 'sspanel/chargecenter.html', context=context)


# 网站后台界面
@permission_required('shadowsocks')
def backend_index(request):
    '''跳转到后台界面'''

    User = SSUser.objects.all()
    # 找到用户的总量
    user_num = len(User)

    # 循环遍历用户的签到人数
    checkin_num = 0
    for user in User:
        if user.get_check_in() == True:
            checkin_num += 1

    # 节点信息状态
    nodes = Node.objects.all()

    # 用户在线情况
    alive_user = Aliveip.objects.all()

    # 收入情况
    income = Donate.objects.all()
    total_income = 0

    for i in income:
        total_income += i.money

    context = {
        'user_num': user_num,
        'checkin_num': checkin_num,
        'nodes': nodes,
        'alive_user': len(alive_user),
        'income_num': len(income),
        'total_income': total_income,
    }

    return render(request, 'backend/index.html', context=context)


@permission_required('shadowsocks')
def backend_node_info(request):
    '''节点编辑界面'''

    nodes = Node.objects.all()
    context = {
        'nodes': nodes,
    }
    return render(request, 'backend/nodeinfo.html', context=context)


@permission_required('shadowsocks')
def node_delete(request, node_id):
    '''删除节点'''
    node = Node.objects.filter(node_id=node_id)
    node.delete()
    nodes = Node.objects.all()

    registerinfo = {
        'title': '删除节点',
        'subtitle': '成功啦',
                    'status': 'success', }

    context = {
        'nodes': nodes,
        'registerinfo': registerinfo
    }
    return render(request, 'backend/nodeinfo.html', context=context)


@permission_required('shadowsocks')
def node_edit(request, node_id):
    '''编辑节点'''
    node = Node.objects.get(node_id=node_id)
    nodes = Node.objects.all()
    # 当为post请求时，修改数据
    if request.method == "POST":
        form = NodeForm(request.POST, instance=node)
        if form.is_valid():
            form.save()
            registerinfo = {
                'title': '修改成功',
                'subtitle': '数据更新成功',
                'status': 'success', }

            context = {
                'nodes': nodes,
                'registerinfo': registerinfo,
            }
            return render(request, 'backend/nodeinfo.html', context=context)
        else:
            registerinfo = {
                'title': '错误',
                'subtitle': '数据填写错误',
                'status': 'error', }

            context = {
                'form': form,
                'registerinfo': registerinfo,
                'node': node,
            }
            return render(request, 'backend/nodeedit.html', context=context)
    # 当请求不是post时，渲染form
    else:
        form = NodeForm(instance=node)
        context = {
            'form': form,
            'node': node,
        }
        return render(request, 'backend/nodeedit.html', context=context)


@permission_required('shadowsocks')
def node_create(request):
    '''创建节点'''
    if request.method == "POST":
        form = NodeForm(request.POST)
        if form.is_valid():
            form.save()

            nodes = Node.objects.all()
            registerinfo = {
                'title': '添加成功',
                'subtitle': '数据更新成功！',
                'status': 'success', }

            context = {
                'nodes': nodes,
                'registerinfo': registerinfo,
            }
            return render(request, 'backend/nodeinfo.html', context=context)
        else:
            registerinfo = {
                'title': '错误',
                'subtitle': '数据填写错误',
                'status': 'error', }

            context = {
                'form': form,
                'registerinfo': registerinfo,
            }
            return render(request, 'backend/nodecreate.html', context=context)

    else:
        form = NodeForm()
        return render(request, 'backend/nodecreate.html', context={'form': form, })

# 弃用


@permission_required('shadowsocks')
def backend_alive_user(request):
    '''用户在线列表'''

    alive_user = Aliveip.objects.all()
    # 每页显示10条记录
    paginator = Paginator(alive_user, 10)
    # 构造分页.获取页码数量
    page = request.GET.get('page')

    page_list = paginator.page_range

    try:
        contacts = paginator.page(page)
    except PageNotAnInteger:
        contacts = paginator.page(1)
    except EmptyPage:
        contacts = paginator.page(paginator.num_pages)

    context = {
        'contacts': contacts,
        'page_list': page_list,
    }

    return render(request, 'backend/aliveuser.html', context=context)


class Page_List_View(object):
    '''拥有翻页功能的通用类'''

    def __init__(self, request, obj, page_num):
        self.request = request
        self.obj = obj
        self.page_num = page_num

    def get_page_context(self):
        '''返回分页context'''

        objects = self.obj.objects.all()
        # 每页显示10条记录
        paginator = Paginator(objects, self.page_num)
        # 构造分页.获取页码数量
        page = self.request.GET.get('page')

        page_list = paginator.page_range

        try:
            contacts = paginator.page(page)
        except PageNotAnInteger:
            contacts = paginator.page(1)
        except EmptyPage:
            contacts = paginator.page(paginator.num_pages)

        context = {
            'contacts': contacts,
            'page_list': page_list,
        }

        return context


@permission_required('shadowsocks')
def Backend_Aliveuser(request):
    '''返回在线用户的ip的View'''

    obj = Aliveip
    page_num = 10
    context = Page_List_View(request, obj, page_num).get_page_context()

    return render(request, 'backend/aliveuser.html', context=context)


@permission_required('shadowsocks')
def Backend_UserList(request):
    '''返回所有用户的View'''

    obj = User
    page_num = 15
    context = Page_List_View(request, obj, page_num).get_page_context()

    return render(request, 'backend/userlist.html', context=context)


@permission_required('shadowsocks')
def user_delete(request, pk):
    '''删除user'''
    user = User.objects.filter(pk=pk)
    user.delete()

    obj = User
    page_num = 15
    context = Page_List_View(request, obj, page_num).get_page_context()

    registerinfo = {
        'title': '删除用户',
        'subtitle': '成功啦',
                    'status': 'success', }

    context['registerinfo'] = registerinfo
    return render(request, 'backend/userlist.html', context=context)


@permission_required('shadowsocks')
def user_search(request):
    '''用户搜索结果'''
    q = request.GET.get('q')
    contacts = User.objects.filter(
        Q(username__icontains=q) | Q(email__icontains=q))
    context = {
        'contacts': contacts,
    }

    return render(request, 'backend/userlist.html', context=context)


@permission_required('shadowsocks')
def backend_invite(request):
    '''邀请码生成'''
    return render(request, 'backend/invitecode.html')


def gen_invite_code(request):

    Num = request.GET.get('num')

    for i in range(int(Num)):
        code = InviteCode()
        code.save()

    registerinfo = {
        'title': '成功',
        'subtitle': '添加邀请码{}个'.format(Num),
                    'status': 'success', }

    context = {
        'registerinfo': registerinfo,
    }

    return render(request, 'backend/invitecode.html', context=context)


@permission_required('shadowsocks')
def backend_charge(request):
    '''后台充值码界面'''

    # 获取所有充值码记录
    obj = MoneyCode
    page_num = 10
    # 获取充值的金额和数量
    Num = request.GET.get('num')
    money = request.GET.get('money')
    if Num and money:
        for i in range(int(Num)):
            code = MoneyCode(number=money)
            code.save()
        context = Page_List_View(request, obj, page_num).get_page_context()
        registerinfo = {
            'title': '成功',
            'subtitle': '添加{}元充值码{}个'.format(money, Num),
            'status': 'success'}
        context['registerinfo'] = registerinfo

    else:
        context = Page_List_View(request, obj, page_num).get_page_context()

    return render(request, 'backend/charge.html', context=context)


@permission_required('shadowsocks')
def backend_shop(request):
    '''商品管理界面'''

    goods = Shop.objects.all()
    context = {
        'goods': goods,
    }
    return render(request, 'backend/shop.html', context=context)


@permission_required('shadowsocks')
def good_delete(request, pk):
    '''删除商品'''
    good = Shop.objects.filter(pk=pk)
    good.delete()
    goods = Shop.objects.all()

    registerinfo = {
        'title': '删除商品',
        'subtitle': '成功啦',
                    'status': 'success', }

    context = {
        'goods': goods,
        'registerinfo': registerinfo
    }
    return render(request, 'backend/shop.html', context=context)


@permission_required('shadowsocks')
def good_edit(request, pk):

    good = Shop.objects.get(pk=pk)
    goods = Shop.objects.all()
    # 当为post请求时，修改数据
    if request.method == "POST":
        form = ShopForm(request.POST, instance=good)
        if form.is_valid():
            form.save()
            registerinfo = {
                'title': '修改成功',
                'subtitle': '数据更新成功',
                'status': 'success', }

            context = {
                'goods': goods,
                'registerinfo': registerinfo,
            }
            return render(request, 'backend/shop.html', context=context)
        else:
            registerinfo = {
                'title': '错误',
                'subtitle': '数据填写错误',
                'status': 'error', }

            context = {
                'form': form,
                'registerinfo': registerinfo,
                'good': good,
            }
            return render(request, 'backend/goodedit.html', context=context)
    # 当请求不是post时，渲染form
    else:
        form = ShopForm(instance=good)
        context = {
            'form': form,
            'good': good,
        }
        return render(request, 'backend/goodedit.html', context=context)


@permission_required('shadowsocks')
def good_create(request):
    if request.method == "POST":
        form = ShopForm(request.POST)
        if form.is_valid():
            form.save()

            goods = Shop.objects.all()
            registerinfo = {
                'title': '添加成功',
                'subtitle': '数据更新成功！',
                'status': 'success', }

            context = {
                'goods': goods,
                'registerinfo': registerinfo,
            }
            return render(request, 'backend/shop.html', context=context)
        else:
            registerinfo = {
                'title': '错误',
                'subtitle': '数据填写错误',
                'status': 'error', }

            context = {
                'form': form,
                'registerinfo': registerinfo,
            }
            return render(request, 'backend/goodcreate.html', context=context)

    else:
        form = ShopForm()
        return render(request, 'backend/goodcreate.html', context={'form': form, })


@permission_required('shadowsocks')
def purchase_history(request):
    obj = PurchaseHistory
    page_num = 10
    context = Page_List_View(request, obj, page_num).get_page_context()
    return render(request, 'backend/purchasehistory.html', context=context)
