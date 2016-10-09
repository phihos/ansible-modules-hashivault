import os
import warnings

import hvac
from ansible.module_utils.basic import AnsibleModule


def hashivault_argspec():
    argument_spec = dict(
        url = dict(required=False, default=os.environ.get('VAULT_ADDR', ''), type='str'),
        verify = dict(required=False, default=(not os.environ.get('VAULT_SKIP_VERIFY', '')), type='bool'),
        authtype = dict(required=False, default='token', type='str'),
        token = dict(required=False, default=os.environ.get('VAULT_TOKEN', ''), type='str'),
        username = dict(required=False, type='str'),
        password = dict(required=False, type='str')
    )
    return argument_spec


def hashivault_init(argument_spec):
    return AnsibleModule(argument_spec=argument_spec)


def hashivault_client(params):
    url = params.get('url')
    verify = params.get('verify')
    token = params.get('token')
    authtype = params.get('authtype')
    token = params.get('token')
    username = params.get('username')
    password = params.get('password')
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        client = hvac.Client(url=url, verify=verify)
        if authtype == 'github':
            client.auth_github(token)
        elif authtype == 'userpass':
            client.auth_userpass(username, password)
        elif authtype == 'ldap':
            client.auth_ldap(username, password)
        else:
            client.token = token
    return client


def hashiwrapper(function):
    def wrapper(*args, **kwargs):
        result = { "changed": False, "rc" : 0}
        try:
            result.update(function(*args, **kwargs))
        except Exception as e:
            import traceback
            result['rc'] = 1
            result['failed'] = True
            result['msg'] = "Exception: " + str(e)
            result['stack_trace'] = traceback.format_exc()
        return result
    return wrapper


@hashiwrapper
def hashivault_status(params):
    client = hashivault_client(params)
    return {'status': client.seal_status}


@hashiwrapper
def hashivault_seal(params):
    key = params.get('key')
    client = hashivault_client(params)
    return {'status': client.seal(), 'changed': True}


@hashiwrapper
def hashivault_unseal(params):
    keys = params.get('keys')
    client = hashivault_client(params)
    return {'status': client.unseal_multi(keys.split()), 'changed': True}

@hashiwrapper
def hashivault_policy_get(params):
    name = params.get('name')
    client = hashivault_client(params)
    return {'rules': client.get_policy(name)}


@hashiwrapper
def hashivault_policy_list(params):
    client = hashivault_client(params)
    return {'policies': client.list_policies()}


@hashiwrapper
def hashivault_policy_set(params):
   client = hashivault_client(params)
   name = params.get('name')
   rules = params.get('rules')
   client.set_policy(name, rules)
   return {'changed': True}


@hashiwrapper
def hashivault_read(params):
    result = { "changed": False, "rc" : 0}
    client = hashivault_client(params)
    secret = params.get('secret')
    key = params.get('key')
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        response = client.read('secret/%s' % secret)
        if not response:
            result['rc'] = 1
            result['failed'] = True
            result['msg'] = "Secret %s is not in vault" % secret
            return result
        data = response['data']
    if key not in data:
        result['rc'] = 1
        result['failed'] = True
        result['msg'] = "Key %s is not in secret %s" % (key, secret)
        return result
    value = data[key]
    result['value'] = value
    return result


@hashiwrapper
def hashivault_write(params):
    result = { "changed": False, "rc" : 0}
    client = hashivault_client(params)
    secret = params.get('secret')
    data = params.get('data')
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if params.get('update'):
            read_data = client.read('secret/%s' % secret)
            if read_data and 'data' in read_data:
                write_data  = read_data['data']
            else:
                write_data  = {}
            write_data.update(data)
            client.write(('secret/%s' % secret), **write_data)
            result['msg'] = "Secret %s updated" % secret
        else:
            client.write(('secret/%s' % secret), **data)
            result['msg'] = "Secret %s written" % secret
    result['changed'] = True
    return result
