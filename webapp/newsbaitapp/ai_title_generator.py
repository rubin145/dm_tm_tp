import openai
from os import getenv
from .models import AIConfiguration, APIKey, AICall
from .system_prompt import default_system_prompt

def ai_title_generator(text, tags):
    
    try:
        ai_config = AIConfiguration.objects.get()
        model = ai_config.model
        api_key = ai_config.api_key_alias
        testing = ai_config.testing
        extra_config = ai_config.extra_config
        system_prompt = ai_config.system_prompt

    except:
        model = "gpt-3.5-turbo"
        api_key='dmtmtp'
        testing=True
        extra_config={}
        system_prompt = default_system_prompt
#     
    # User input is appended to the system prompt
    input_prompt = f"TEXTO DE LA NOTICIA: {text}\n ETIQUETAS DEL USUARIO: {tags}"
    
    # Retrieve API key securely
    openai.api_key = APIKey.objects.get(alias=api_key).key  #getenv('OPENAI_API_KEY')  # Make sure to set your OPENAI_API_KEY environment variable
    
    # Configuration for the request
    configuration = {
        "model": model, #"text-davinci-003",  # replace with your chosen model #instead of engine
        "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_prompt}        
        ],
        ##"headers": {"OpenAI-Organization": organizations[organization]},
        **extra_config
        #"temperature": 0.7,
        #"max_tokens": 150
        # etc
    }
    try:
        response = openai.ChatCompletion.create(**configuration)
        input_token_count = getattr(getattr(response,'usage',None),'prompt_tokens',0)
        output_token_count = getattr(getattr(response,'usage',None),'completion_tokens',0)
        input_spend = compute_quota_spend(model,input_token_count,'input')
        output_spend = compute_quota_spend(model,output_token_count,'output')
        total_spend = input_spend + output_spend
        organization_ = getattr(response,'organization','')
        n_choices = len(getattr(response,'choices',[]))
        choices = getattr(response,'choices',[])
        model_ = getattr(response,'model','')

        result = {
            #'response':response,
            'title': response['choices'][0]['message']['content'].strip(),
            'input_token_count': input_token_count,
            'output_token_count': output_token_count,
            'input_spend': input_spend,
            'output_spend': output_spend,
            'total_spend': total_spend,
            'organization': organization_,
            'n_choices': n_choices,
            'choices': choices,
            'model_resp': model_,
            'model_arg': model,
            'system_prompt': system_prompt,
            'input_prompt': input_prompt,
            #'organization': organizations[organization],
            'api_key_alias':api_key,
            'extra_config':extra_config,
            'testing':testing
            } #.choices[0].text.strip()   response['choices'][0]['message']['content'].strip()
        try:
            ai_call = AICall.objects.create(**result)
            ai_call.save()
        except Exception as e:
            print(f'AICall could not be registered in database: {e}')
            pass      
        return result
    except openai.error.OpenAIError as e:
        # Handle API errors
        print(f"An error occurred: {e}")
        return None

def compute_quota_spend(model,n_tokens,input_output):
    if model not in list(openai_models.keys()):
        raise Exception("model not listed")
    if input_output not in ['input','output']:
        raise Exception("bad argument")
    try: 
        return n_tokens * openai_models[model]['pricing'][input_output]
    except:
        return 0 #esto es cualquiera

organizations = {
    'Exactas': 'org-aM1Vg80QIO4u9gr3TRLYt1b0',
    'Personal': 'org-wxP3EOvvec1sV71ABOn9zIeQ'
}

openai_models = {
    "gpt-4" : {
        'max_tokens': 8192,
        'pricing': {
            'input': 0.03/1000,
            'output': 0.06/1000
            }
        },
    "gpt-4-0613" : {'max_tokens': 8192,
               'pricing': {'input':0.03/1000,
                           'output':0.06/1000
                           }
                },
    "gpt-4-32k" : {'max_tokens': 32768,
               'pricing': {'input':0.06/1000,
                           'output':0.12/1000
                           }
                },
    "gpt-4-32k-0613" : {'max_tokens': 32768,
               'pricing': {'input':0.06/1000,
                           'output':0.12/1000
                           }
                },
    "gpt-4-0314" : {'max_tokens': 8192,
               'pricing': {'input':0.03/1000,
                           'output':0.06/1000
                           }
                },
    "gpt-4-32k-0314" : {'max_tokens': 32768,
               'pricing': {'input':0.06/1000,
                           'output':0.12/1000
                           }
                },
    "gpt-3.5-turbo" : {'max_tokens': 4097,
               'pricing': {'input':0.0015/1000,
                           'output':0.002/1000
                           }
                },
    "gpt-3.5-turbo-16k" : {'max_tokens': 16385,
               'pricing': {'input':0.003/1000,
                           'output':0.004/1000
                           }
                },
    "gpt-3.5-turbo-instruct" : {'max_tokens': 4097,
               'pricing': {'input':0.0015/1000,
                           'output':0.002/1000
                           }
                },
    "gpt-3.5-turbo-0613" : {'max_tokens': 4097,
               'pricing': {'input':0.0015/1000,
                           'output':0.002/1000
                           }
                },
    "gpt-3.5-turbo-16k-0613" : {'max_tokens': 16385,
               'pricing': {'input':0.003/1000,
                           'output':0.004/1000
                           }
                },
    "gpt-3.5-turbo-0301" : {'max_tokens': 4097,
               'pricing': {'input':0.0015/1000,
                           'output':0.002/1000
                           }
                },
    "text-davinci-003" : {'max_tokens': 4097, #estos creo que son más baratos
               'pricing': {'input':0.0015/1000,
                           'output':0.002/1000
                           }
                },
    "text-davinci-002" : {'max_tokens': 4097, #estos creo que son más baratos
               'pricing': {'input':0.0015/1000,
                           'output':0.002/1000
                           }
                }
}