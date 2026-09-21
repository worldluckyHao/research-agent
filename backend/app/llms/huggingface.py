import logging
from typing import Optional

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)

from backend.app.llms.base import (
    LLMGenerationResult,
    LLMProvider,
)


logger = logging.getLogger(__name__)


class HuggingFaceLLMProvider(
    LLMProvider
):
    """
    本地 Hugging Face Chat Model Provider。

    Day30 默认：
        Qwen2.5-1.5B-Instruct
    """

    name = "huggingface"


    def __init__(
        self,
        model_name: str,
        device: str,
        max_new_tokens: int,
        temperature: float,
        do_sample: bool,
    ):
        self.model_name = (
            model_name
        )

        self.configured_device = (
            device
        )

        self.max_new_tokens = (
            max_new_tokens
        )

        self.temperature = (
            temperature
        )

        self.do_sample = (
            do_sample
        )


        # Lazy Loading（延迟加载）
        self._tokenizer = None

        self._model = None

        self._resolved_device: Optional[
            str
        ] = None


    def _resolve_device(
        self,
    ) -> str:
        """
        自动选择模型运行设备。
        """

        if (
            self.configured_device
            != "auto"
        ):
            return (
                self.configured_device
            )


        if torch.cuda.is_available():
            return "cuda"


        return "cpu"


    def _load(
        self,
    ):
        """
        第一次真正调用 LLM 时加载模型。
        """

        if (
            self._model is not None
            and self._tokenizer is not None
        ):
            return


        device = (
            self._resolve_device()
        )


        logger.info(
            (
                "Loading LLM: "
                "model=%s device=%s"
            ),
            self.model_name,
            device,
        )


        tokenizer = (
            AutoTokenizer
            .from_pretrained(
                self.model_name,
            )
        )


        # CUDA 下使用 float16，
        # 减少显存占用。
        if device == "cuda":

            model = (
                AutoModelForCausalLM
                .from_pretrained(
                    self.model_name,

                    torch_dtype=(
                        torch.float16
                    ),
                )
            )

            model = model.to(
                device
            )


        else:

            model = (
                AutoModelForCausalLM
                .from_pretrained(
                    self.model_name,
                )
            )

            model = model.to(
                device
            )


        model.eval()


        self._tokenizer = tokenizer

        self._model = model

        self._resolved_device = (
            device
        )


        logger.info(
            (
                "LLM loaded: "
                "model=%s device=%s"
            ),
            self.model_name,
            device,
        )


    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMGenerationResult:
        """
        使用模型 Chat Template
        完成生成。
        """

        self._load()


        tokenizer = (
            self._tokenizer
        )

        model = (
            self._model
        )


        messages = [
            {
                "role": "system",
                "content": (
                    system_prompt
                ),
            },
            {
                "role": "user",
                "content": (
                    user_prompt
                ),
            },
        ]


        prompt_text = (
            tokenizer
            .apply_chat_template(
                messages,

                tokenize=False,

                add_generation_prompt=True,
            )
        )


        inputs = tokenizer(
            prompt_text,
            return_tensors="pt",
        )


        inputs = {
            key: value.to(
                self._resolved_device
            )
            for key, value
            in inputs.items()
        }


        generation_kwargs = {
            "max_new_tokens":
                self.max_new_tokens,

            "do_sample":
                self.do_sample,
        }


        # temperature 在 do_sample=False 时
        # 没有实际作用，
        # 因此只在 Sampling 模式加入。
        if self.do_sample:

            generation_kwargs[
                "temperature"
            ] = self.temperature


        with torch.inference_mode():

            output_ids = model.generate(
                **inputs,
                **generation_kwargs,
            )


        # generate() 返回：
        #
        # prompt tokens
        # +
        # generated tokens
        #
        # 所以只切出新增部分。
        input_length = (
            inputs[
                "input_ids"
            ].shape[1]
        )


        generated_ids = (
            output_ids[
                0,
                input_length:
            ]
        )


        text = tokenizer.decode(
            generated_ids,
            skip_special_tokens=True,
        ).strip()


        return (
            LLMGenerationResult(
                text=text,

                provider=self.name,

                model_name=(
                    self.model_name
                ),
            )
        )


    def get_model_name(
        self,
    ) -> str:

        return self.model_name