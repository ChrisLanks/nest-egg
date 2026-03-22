/**
 * Listens for "api-error-toast" custom events dispatched by the axios
 * interceptor (api.ts) and shows Chakra toasts using the app's single
 * ToastProvider.  This avoids the duplicate-key warning that occurred
 * when createStandaloneToast was used (it creates a second provider).
 */
import { useEffect } from "react";
import { useToast } from "@chakra-ui/react";

export function ApiErrorToastListener() {
  const toast = useToast();

  useEffect(() => {
    const handler = (e: Event) => {
      const { type } = (e as CustomEvent<{ type: string }>).detail;
      if (type === "rate-limit") {
        if (!toast.isActive("rate-limit-toast")) {
          toast({
            id: "rate-limit-toast",
            title: "Too many requests",
            description: "You're doing that too fast. Please wait a moment and try again.",
            status: "warning",
            duration: 5000,
            isClosable: true,
          });
        }
      } else if (type === "server-error") {
        if (!toast.isActive("server-error-toast")) {
          toast({
            id: "server-error-toast",
            title: "Server error",
            description: "Something went wrong on our end. Please try again.",
            status: "error",
            duration: 5000,
            isClosable: true,
          });
        }
      }
    };
    window.addEventListener("api-error-toast", handler);
    return () => window.removeEventListener("api-error-toast", handler);
  }, [toast]);

  return null;
}
