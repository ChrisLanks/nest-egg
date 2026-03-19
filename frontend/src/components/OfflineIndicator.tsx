/**
 * OfflineIndicator — shows a banner at the top of the page when the browser
 * loses its network connection, and dismisses automatically on reconnect.
 */

import { Alert, AlertIcon, AlertTitle, Collapse, Text } from "@chakra-ui/react";
import { useEffect, useState } from "react";

export const OfflineIndicator = () => {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const handleOffline = () => setIsOffline(true);
    const handleOnline = () => setIsOffline(false);

    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);
    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, []);

  return (
    <Collapse in={isOffline} animateOpacity>
      <Alert status="warning" borderRadius={0} px={6} py={2}>
        <AlertIcon />
        <AlertTitle mr={2} fontSize="sm">
          You're offline.
        </AlertTitle>
        <Text fontSize="sm" color="inherit">
          Data shown may be out of date. Changes will sync when you reconnect.
        </Text>
      </Alert>
    </Collapse>
  );
};
