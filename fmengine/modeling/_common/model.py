import torch
from transformers.configuration_utils import PretrainedConfig
from transformers.models.llama.modeling_llama import LlamaConfig
from transformers.models.gpt_neox.modeling_gpt_neox import GPTNeoXConfig
from transformers.models.mistral.modeling_mistral import MistralConfig
from deepspeed.runtime.pipe.topology import PipeModelDataParallelTopology
from fmengine.optimizers.loss_func import cross_entropy_fn


def get_model(
    model_config: PretrainedConfig,
    args,
    activation_checkpointing_config=None,
):
    pp = args.pipe_parallel_size
    mp = args.model_parallel_size
    assert args.world_size % (pp * mp) == 0
    dp = args.world_size // (pp * mp)

    topo = PipeModelDataParallelTopology(num_pp=pp, num_mp=mp, num_dp=dp)
    # Offset base seeds for the interior pipeline stages.
    stage_id = topo.get_coord(rank=torch.distributed.get_rank()).pipe
    if 0 < stage_id < topo.get_dim("pipe") - 1:
        args.seed = args.seed + (stage_id * mp)
    if isinstance(model_config, LlamaConfig):
        from fmengine.modeling.llama.llama_model import LlamaModelPipe
        
        return LlamaModelPipe(
            args,
            model_config,
            loss_fn=cross_entropy_fn,
            topology=topo,
            base_seed=args.seed,
            activation_checkpointing_config=activation_checkpointing_config,
        )
    elif isinstance(model_config, GPTNeoXConfig):
        from fmengine.modeling.neox.neox_model import NeoxModelPipe
        
        return NeoxModelPipe(
            args,
            model_config,
            loss_fn=cross_entropy_fn,
            topology=topo,
            base_seed=args.seed,
            activation_checkpointing_config=activation_checkpointing_config,
        )
    elif isinstance(model_config, MistralConfig):
        from fmengine.modeling.mistral.mistral_model import MistralModelPipe
        
        return MistralModelPipe(
            args,
            model_config,
            loss_fn=cross_entropy_fn,
            topology=topo,
            base_seed=args.seed,
            activation_checkpointing_config=activation_checkpointing_config,
        )
    else:
        raise NotImplementedError
