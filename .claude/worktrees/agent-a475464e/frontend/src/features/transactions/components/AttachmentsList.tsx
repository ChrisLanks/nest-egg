/**
 * Attachments list with upload/download for transaction detail
 */

import {
  Box,
  Button,
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
import { useRef } from "react";
import { attachmentsApi, type Attachment } from "../../../api/attachments";

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

interface AttachmentsListProps {
  transactionId: string;
  canEdit: boolean;
}

export const AttachmentsList = ({
  transactionId,
  canEdit,
}: AttachmentsListProps) => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

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
