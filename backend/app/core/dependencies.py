from functools import lru_cache

from app.agents.dialogue_flow import DialogueFlowController
from app.agents.input_preprocessor import InputPreprocessor
from app.agents.frontend_action_planner import FrontendActionPlanner
from app.agents.frontend_event_builder import FrontendEventBuilder
from app.agents.intent_parser import IntentParser
from app.agents.model_router import ModelRouter
from app.agents.product_qa import ProductQAModule
from app.agents.query_understanding import QueryUnderstandingModule
from app.agents.response_generator import ResponseGenerationModule
from app.agents.scene_presentation_builder import ScenePresentationBuilder
from app.agents.response_validator import ResponseValidator
from app.agents.scenario_planner import ScenarioPlanner
from app.agents.shopping_agent import ShoppingAgent
from app.agents.task_planner import TaskPlanner
from app.core.config import settings
from app.llm.base import BaseLLMClient
from app.llm.doubao_client import DoubaoClient
from app.llm.mock_llm import MockLLMClient
from app.memory.preference_manager import PreferenceManager
from app.memory.cart_aware_personalization import CartAwarePersonalization
from app.memory.personalization_service import PersonalizationService
from app.memory.session_memory import SessionMemory
from app.memory.user_history_store import UserHistoryStore
from app.memory.user_profile_service import UserProfileService
from app.ml.local_models import LocalModelManager
from app.multimodal.image_loader import ImageLoader
from app.multimodal.image_preprocessor import ImagePreprocessor
from app.multimodal.multimodal_service import MultimodalService
from app.multimodal.vision_analyzer import VisionAnalyzer
from app.multimodal.visual_query_builder import VisualQueryBuilder
from app.multimodal.visual_product_matcher import VisualProductMatcher
from app.multimodal.visual_retriever import VisualRetriever
from app.progress.progress_event_builder import ProgressEventBuilder
from app.repositories.product_repository import ProductRepository
from app.rag.pipeline import RagPipeline
from app.retrieval.base import BaseRetriever
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.post_processor import ProductPostProcessor
from app.services.cart_service import CartService
from app.services.checkout_service import CheckoutService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.speech_service import SpeechService
from app.tools.action_executor import ActionExecutor
from app.tools.cart_tool import CartTool
from app.tools.checkout_tool import CheckoutTool
from app.tools.order_tool import OrderTool
from app.tools.product_search_tool import ProductSearchTool
from app.tools.rag_tool import RagTool


@lru_cache
def get_product_repository() -> ProductRepository:
    return ProductRepository(
        source_path=settings.product_data_path,
        dataset_dir=settings.product_dataset_dir,
    )


@lru_cache
def get_product_service() -> ProductService:
    return ProductService(product_repository=get_product_repository())


@lru_cache
def get_speech_service() -> SpeechService:
    return SpeechService(
        enabled=settings.enable_speech,
        upload_dir=settings.speech_upload_dir,
        tts_dir=settings.tts_output_dir,
        asr_backend=settings.asr_backend,
        asr_model_name=settings.asr_model_name,
        tts_backend=settings.tts_backend,
        tts_voice=settings.tts_voice,
        macos_tts_voice=settings.macos_tts_voice,
        max_audio_mb=settings.speech_max_audio_mb,
    )


@lru_cache
def get_session_memory() -> SessionMemory:
    return SessionMemory()


@lru_cache
def get_user_history_store() -> UserHistoryStore:
    return UserHistoryStore(root_dir=settings.user_history_dir)


@lru_cache
def get_user_profile_service() -> UserProfileService:
    return UserProfileService(
        history_store=get_user_history_store(),
        llm_client=get_llm_client(),
    )


@lru_cache
def get_personalization_service() -> PersonalizationService:
    return PersonalizationService(
        history_store=get_user_history_store(),
        local_models=get_local_model_manager(),
    )


@lru_cache
def get_cart_aware_personalization() -> CartAwarePersonalization:
    return CartAwarePersonalization(
        product_repository=get_product_repository(),
        llm_client=get_llm_client(),
    )


@lru_cache
def get_progress_event_builder() -> ProgressEventBuilder:
    return ProgressEventBuilder()


@lru_cache
def get_multimodal_service() -> MultimodalService:
    return MultimodalService(
        enabled=settings.enable_multimodal,
        image_loader=ImageLoader(upload_dir=settings.upload_image_dir),
        image_preprocessor=ImagePreprocessor(),
        vision_analyzer=VisionAnalyzer(
            llm_client=get_llm_client(),
            vision_model=settings.vision_model,
        ),
        visual_query_builder=VisualQueryBuilder(),
        visual_product_matcher=VisualProductMatcher(
            product_repository=get_product_repository(),
            dataset_dir=settings.product_dataset_dir,
        ),
        visual_retriever=VisualRetriever(),
    )


@lru_cache
def get_cart_service() -> CartService:
    return CartService(
        session_memory=get_session_memory(),
        product_repository=get_product_repository(),
    )


@lru_cache
def get_checkout_service() -> CheckoutService:
    return CheckoutService(cart_service=get_cart_service())


@lru_cache
def get_order_service() -> OrderService:
    return OrderService()


@lru_cache
def get_retriever() -> BaseRetriever:
    return HybridRetriever(
        product_repository=get_product_repository(),
        local_models=get_local_model_manager(),
    )


@lru_cache
def get_rag_pipeline() -> RagPipeline:
    return RagPipeline()


@lru_cache
def get_product_search_tool() -> ProductSearchTool:
    return ProductSearchTool(retriever=get_retriever())


@lru_cache
def get_rag_tool() -> RagTool:
    return RagTool(pipeline=get_rag_pipeline())


@lru_cache
def get_cart_tool() -> CartTool:
    return CartTool(cart_service=get_cart_service())


@lru_cache
def get_checkout_tool() -> CheckoutTool:
    return CheckoutTool(checkout_service=get_checkout_service())


@lru_cache
def get_order_tool() -> OrderTool:
    return OrderTool(order_service=get_order_service())


@lru_cache
def get_intent_parser() -> IntentParser:
    return IntentParser()


@lru_cache
def get_query_understanding() -> QueryUnderstandingModule:
    return QueryUnderstandingModule(
        product_repository=get_product_repository(),
        local_models=get_local_model_manager(),
        llm_client=get_llm_client(),
    )


@lru_cache
def get_input_preprocessor() -> InputPreprocessor:
    return InputPreprocessor()


@lru_cache
def get_model_router() -> ModelRouter:
    return ModelRouter(local_models=get_local_model_manager())


@lru_cache
def get_local_model_manager() -> LocalModelManager:
    return LocalModelManager(
        enable=settings.enable_local_models,
        bge_embedding_path=settings.bge_embedding_model_path,
        text2vec_path=settings.text2vec_model_path,
        reranker_path=settings.bge_reranker_model_path,
        device=settings.local_model_device,
    )


@lru_cache
def get_flow_controller() -> DialogueFlowController:
    return DialogueFlowController()


@lru_cache
def get_task_planner() -> TaskPlanner:
    return TaskPlanner()


@lru_cache
def get_post_processor() -> ProductPostProcessor:
    return ProductPostProcessor()


@lru_cache
def get_action_executor() -> ActionExecutor:
    return ActionExecutor(
        cart_service=get_cart_service(),
        product_repository=get_product_repository(),
        order_service=get_order_service(),
    )


@lru_cache
def get_preference_manager() -> PreferenceManager:
    return PreferenceManager()


@lru_cache
def get_product_qa_module() -> ProductQAModule:
    return ProductQAModule()


@lru_cache
def get_scenario_planner() -> ScenarioPlanner:
    return ScenarioPlanner()


@lru_cache
def get_llm_client() -> BaseLLMClient:
    if settings.use_mock_llm:
        return MockLLMClient()
    return DoubaoClient(
        api_key=settings.doubao_api_key,
        base_url=settings.doubao_base_url,
        model=settings.doubao_model,
    )


@lru_cache
def get_response_generator() -> ResponseGenerationModule:
    return ResponseGenerationModule(
        rag_pipeline=get_rag_pipeline(),
        llm_client=get_llm_client(),
    )


@lru_cache
def get_response_validator() -> ResponseValidator:
    return ResponseValidator(known_products=get_product_repository().list_products())


@lru_cache
def get_frontend_action_planner() -> FrontendActionPlanner:
    return FrontendActionPlanner(llm_client=get_llm_client())


@lru_cache
def get_frontend_event_builder() -> FrontendEventBuilder:
    return FrontendEventBuilder()


@lru_cache
def get_scene_presentation_builder() -> ScenePresentationBuilder:
    return ScenePresentationBuilder(llm_client=get_llm_client())


@lru_cache
def get_shopping_agent() -> ShoppingAgent:
    return ShoppingAgent(
        query_understanding=get_query_understanding(),
        input_preprocessor=get_input_preprocessor(),
        model_router=get_model_router(),
        flow_controller=get_flow_controller(),
        task_planner=get_task_planner(),
        session_memory=get_session_memory(),
        product_repository=get_product_repository(),
        product_search_tool=get_product_search_tool(),
        post_processor=get_post_processor(),
        action_executor=get_action_executor(),
        preference_manager=get_preference_manager(),
        product_qa_module=get_product_qa_module(),
        scenario_planner=get_scenario_planner(),
        response_generator=get_response_generator(),
        response_validator=get_response_validator(),
        scene_presentation_builder=get_scene_presentation_builder(),
        frontend_action_planner=get_frontend_action_planner(),
        frontend_event_builder=get_frontend_event_builder(),
        user_history_store=get_user_history_store(),
        user_profile_service=get_user_profile_service(),
        personalization_service=get_personalization_service(),
        multimodal_service=get_multimodal_service(),
        progress_event_builder=get_progress_event_builder(),
        cart_aware_personalization=get_cart_aware_personalization(),
    )
