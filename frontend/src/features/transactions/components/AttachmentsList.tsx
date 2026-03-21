/**
 * Attachments list with upload/download for transaction detail.
 * After upload, shows an OCR suggestion banner if receipt data was extracted.
 */

import {
  Alert,
  AlertIcon,
  Box,
  Button,
  CloseButton,
  HStack,
  IconButton,
  Input,
  Spinner,
  Text,
  Tooltip,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { FiDownload, FiPaperclip, FiTrash2, FiUpload } from "react-icons/fi";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import {
  attachmentsApi,
  type Attachment,
  type OcrData,
} from "../../../api/attachments";

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export interface OcrSuggestion {
  merchant: string | null;
  amount: string | null;
  date: string | null;
}

interface AttachmentsListProps {
  transactionId: string;
  canEdit: boolean;
  /** Called when user clicks "Apply to transaction" on an OCR suggestion. */
  onApplyOcrSuggestion?: (suggestion: OcrSuggestion) => void;
}

/** Return the first attachment with usable OCR data, or null. */
function findOcrSuggestion(
  attachments: Attachment[],
): { attachmentId: string; data: OcrData } | null {
  for (const att of attachments) {
    if (
      att.ocr_status === "completed" &&
      att.ocr_data &&
      (att.ocr_data.merchant || att.ocr_data.amount)
    ) {
      return { attachmentId: att.id, data: att.ocr_data };
    }
  }
  return null;
}

export const AttachmentsList = ({
  transactionId,
  canEdit,
  onApplyOcrSuggestion,
}: AttachmentsListProps) => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dismissedOcrId, setDismissedOcrId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["attachments", transactionId],
    queryFn: () => attachmentsApi.list(transactionId),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => attachmentsApi.upload(transactionId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["attachments", transactionId],
      });
      toast({
        title: "Attachment uploaded",
        status: "success",
        duration: 3000,
      });
    },
    onError: (error: unknown) => {
      const detail =
        (error as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Upload failed";
      toast({
        title: "Upload failed",
        description: detail,
        status: "error",
        duration: 5000,
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (attachmentId: string) => attachmentsApi.delete(attachmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["attachments", transactionId],
      });
      toast({ title: "Attachment deleted", status: "success", duration: 3000 });
    },
    onError: () => {
      toast({ title: "Delete failed", status: "error", duration: 3000 });
    },
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Max 10 MB",
        status: "error",
        duration: 3000,
      });
      return;
    }
    uploadMutation.mutate(file);
    e.target.value = "";
  };

  const handleDownload = (attachment: Attachment) => {
    const url = attachmentsApi.download(attachment.id);
    window.open(url, "_blank");
  };

  const attachments = data?.attachments || [];
  const atLimit = attachments.length >= 5;

  // OCR suggestion banner
  const ocrMatch = findOcrSuggestion(attachments);
  const showOcrBanner =
    !!ocrMatch &&
    ocrMatch.attachmentId !== dismissedOcrId &&
    !!onApplyOcrSuggestion;

  const handleApplyOcr = () => {
    if (!ocrMatch) return;
    onApplyOcrSuggestion?.({
      merchant: ocrMatch.data.merchant,
      amount: ocrMatch.data.amount,
      date: ocrMatch.data.date,
    });
    setDismissedOcrId(ocrMatch.attachmentId);
  };

  return (
    <Box>
      <HStack justify="space-between" mb={2}>
        <HStack spacing={1}>
          <FiPaperclip size={14} />
          <Text fontSize="sm" fontWeight="semibold">
            Attachments {attachments.length > 0 && `(${attachments.length})`}
          </Text>
        </HStack>
        {canEdit && !atLimit && (
          <>
            <Input
              ref={fileInputRef}
              type="file"
              display="none"
              accept="image/*,application/pdf"
              onChange={handleFileSelect}
            />
            <Button
              size="xs"
              variant="outline"
              leftIcon={<FiUpload />}
              onClick={() => fileInputRef.current?.click()}
              isLoading={uploadMutation.isPending}
            >
              Upload
            </Button>
          </>
        )}
      </HStack>

      {/* OCR suggestion banner */}
      {showOcrBanner && ocrMatch && (
        <Alert status="info" borderRadius="md" mb={2} fontSize="xs" py={2}>
          <AlertIcon boxSize={4} />
          <Box flex={1}>
            <Text fontWeight="semibold" mb={0.5}>
              Receipt data detected
            </Text>
            <Text color="text.secondary">
              {[
                ocrMatch.data.merchant &&
                  `Merchant: "${ocrMatch.data.merchant}"`,
                ocrMatch.data.amount && `Amount: $${ocrMatch.data.amount}`,
                ocrMatch.data.date && `Date: ${ocrMatch.data.date}`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </Text>
            <HStack spacing={2} mt={1.5}>
              <Button
                size="xs"
                colorScheme="blue"
                variant="solid"
                onClick={handleApplyOcr}
              >
                Apply to transaction
              </Button>
              <Button
                size="xs"
                variant="ghost"
                onClick={() => setDismissedOcrId(ocrMatch.attachmentId)}
              >
                Dismiss
              </Button>
            </HStack>
          </Box>
          <CloseButton
            size="sm"
            alignSelf="flex-start"
            onClick={() => setDismissedOcrId(ocrMatch.attachmentId)}
          />
        </Alert>
      )}

      {isLoading ? (
        <Spinner size="sm" />
      ) : attachments.length === 0 ? (
        <Text fontSize="xs" color="text.muted">
          No attachments
        </Text>
      ) : (
        <VStack spacing={1} align="stretch">
          {attachments.map((att: Attachment) => (
            <HStack
              key={att.id}
              justify="space-between"
              px={2}
              py={1}
              bg="bg.subtle"
              borderRadius="md"
              fontSize="xs"
            >
              <HStack spacing={2} flex={1} minW={0}>
                <Text noOfLines={1} flex={1}>
                  {att.original_filename}
                </Text>
                <Text color="text.muted" flexShrink={0}>
                  {formatFileSize(att.file_size)}
                </Text>
              </HStack>
              <HStack spacing={1}>
                <Tooltip label="Download">
                  <IconButton
                    aria-label="Download"
                    icon={<FiDownload />}
                    size="xs"
                    variant="ghost"
                    onClick={() => handleDownload(att)}
                  />
                </Tooltip>
                {canEdit && (
                  <Tooltip label="Delete">
                    <IconButton
                      aria-label="Delete"
                      icon={<FiTrash2 />}
                      size="xs"
                      variant="ghost"
                      colorScheme="red"
                      onClick={() => deleteMutation.mutate(att.id)}
                      isLoading={deleteMutation.isPending}
                    />
                  </Tooltip>
                )}
              </HStack>
            </HStack>
          ))}
        </VStack>
      )}

      {atLimit && (
        <Text fontSize="xs" color="text.muted" mt={1}>
          Maximum 5 attachments reached
        </Text>
      )}
    </Box>
  );
};
