from enum import StrEnum


class EventType(StrEnum):
    BLOCK_STANDARDIZATION_COMPLETED = "BlockStandardizationCompleted"
    BLOCK_SUMMARIZATION_COMPLETED = "BlockSummarizationCompleted"
    BLOCK_REFINEMENT_COMPLETED = "BlockRefinementCompleted"
    DOCUMENT_SUMMARY_GENERATED = "DocumentSummaryGenerated"
    SEED_QUESTIONS_GENERATED = "SeedQuestionsGenerated"
    FEATURE_EXTRACTION_COMPLETED = "FeatureExtractionCompleted"
    DOCUMENT_EXTRACTION_COMPLETED = "DocumentExtractionCompleted"
    DOCUMENT_EXTRACTION_STARTED = "DocumentExtractionStarted"
    S3_OBJECT_CREATED = "Object Created"
    SPLIT_FILE_COMPLETED = "SplitFileCompleted"
    TEXT_EXTRACT_SYNC_COMPLETED = "TextExtractSyncCompleted"
