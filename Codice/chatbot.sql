-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Creato il: Dic 15, 2025 alle 12:59
-- Versione del server: 10.4.32-MariaDB
-- Versione PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `chatbot`
--

-- --------------------------------------------------------

--
-- Struttura della tabella `faq`
--

CREATE TABLE `faq` (
  `id` int(11) NOT NULL,
  `categoria` varchar(100) DEFAULT 'generale',
  `domanda` text NOT NULL,
  `risposta1` text DEFAULT NULL,
  `risposta2` text DEFAULT NULL,
  `risposta3` text DEFAULT NULL,
  `data_aggiornamento` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dump dei dati per la tabella `faq`
--

INSERT INTO `faq` (`id`, `categoria`, `domanda`, `risposta1`, `risposta2`, `risposta3`, `data_aggiornamento`) VALUES
(1, 'generale', 'ciao', 'Ciao! Come posso aiutarti?', 'Salve! In cosa posso esserti utile?', 'Ciao! Hai bisogno di assistenza?', '2025-10-31 11:24:57'),
(3, 'generale', 'chi sei', 'Sono il Copilot Utixo, il tuo assistente digitale. Ti aiuto a trovare risposte rapide su domini, email, hosting e servizi cloud.', 'Sono il Copilot Utixo! Un assistente virtuale pensato per supportarti nelle attività tecniche e nei servizi Utixo.', 'Sono il chatbot di Utixo, progettato per darti supporto veloce su configurazioni, problemi tecnici e informazioni sui servizi.', '2025-12-05 11:45:23'),
(4, 'generale', 'cosa puoi fare', 'Posso aiutarti con domande su hosting, email, DNS, Microsoft 365 e molti altri servizi Utixo.', 'Ti supporto nella risoluzione di problemi tecnici, configurazioni e informazioni sui servizi Utixo.', 'Sono in grado di fornirti assistenza su email, dominio, hosting, pannelli di gestione e soluzioni cloud.', '2025-12-05 11:45:23'),
(5, 'generale', 'come funziona il supporto utixo', 'Il supporto Utixo è attivo tramite ticket, telefono e area clienti. I tecnici rispondono in base alla priorità e alla tipologia del servizio.', 'Puoi aprire un ticket dall’area clienti Utixo: un tecnico prenderà in carico la tua richiesta e ti aggiornerà fino alla risoluzione.', 'Il supporto avviene tramite ticket system: apri una richiesta e un tecnico Utixo ti risponderà il prima possibile.', '2025-12-05 11:45:23'),
(6, 'generale', 'come contatto assistenza', 'Puoi contattare l assistenza Utixo aprendo un ticket dall’area clienti.', 'Per ricevere supporto apri un ticket tramite la tua area riservata Utixo.', 'L assistenza tecnica risponde tramite ticket: accedi alla tua area clienti e apri una richiesta.', '2025-12-05 11:45:23'),
(7, 'generale', 'quali servizi offre utixo', 'Utixo offre hosting, email professionali, PEC, DNS, soluzioni cloud e Microsoft 365.', 'I servizi Utixo includono hosting condiviso, server cloud, email, PEC, backup, sicurezza e prodotti Microsoft.', 'Utixo fornisce servizi di hosting, posta elettronica, PEC, cloud, sicurezza IT e soluzioni Microsoft 365.', '2025-12-05 11:45:23'),
(8, 'generale', 'dove trovo area clienti', 'Puoi accedere all area clienti Utixo su https://shop.serverweb.net inserendo le tue credenziali.', 'L area clienti Utixo è disponibile sul portale ufficiale: https://shop.serverweb.net.', 'Accedi alla tua area riservata Utixo tramite https://shop.serverweb.net con username e password.', '2025-12-05 11:45:23'),
(9, 'generale', 'come recupero password area clienti', 'Clicca su Password Dimenticata nella pagina di login dell area clienti Utixo e inserisci la tua email.', 'Per recuperare la password dell area clienti premi su Recupera Password nella schermata di accesso.', 'Nella pagina di login dell area clienti trovi l’opzione Password Dimenticata per reimpostare la tua password.', '2025-12-05 11:45:23'),
(10, 'generale', 'non riesco ad accedere area clienti', 'Assicurati di usare l email con cui hai registrato il tuo account e prova a reimpostare la password.', 'Se non riesci ad accedere prova Recupero Password o verifica che l email sia quella corretta.', 'Puoi provare a reimpostare la password o aprire un ticket per assistenza all accesso.', '2025-12-05 11:45:23'),
(11, 'generale', 'dove trovo le fatture', 'Le fatture sono disponibili nell area clienti Utixo, sezione Fatture.', 'Puoi scaricare le tue fatture dall area clienti andando su Fatture > Documenti.', 'Le fatture Utixo sono visibili e scaricabili nella sezione dedicata dell area clienti.', '2025-12-05 11:45:23'),
(12, 'generale', 'come pago una fattura utixo', 'Puoi pagare le fatture tramite PayPal, carta, bonifico o direttamente dall area clienti.', 'Per pagare una fattura accedi all area clienti Utixo e clicca su Paga accanto alla fattura.', 'Le fatture Utixo possono essere saldate nell area clienti usando carta, PayPal o bonifico.', '2025-12-05 11:45:23');

-- --------------------------------------------------------

--
-- Struttura della tabella `logs`
--

CREATE TABLE `logs` (
  `id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `messaggio_utente` text NOT NULL,
  `risposta_bot` text DEFAULT NULL,
  `data_ora` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Struttura della tabella `utenti`
--

CREATE TABLE `utenti` (
  `id` int(11) NOT NULL,
  `nome` varchar(100) DEFAULT NULL,
  `email` varchar(150) DEFAULT NULL,
  `data_creazione` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Indici per le tabelle scaricate
--

--
-- Indici per le tabelle `faq`
--
ALTER TABLE `faq`
  ADD PRIMARY KEY (`id`);

--
-- Indici per le tabelle `logs`
--
ALTER TABLE `logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indici per le tabelle `utenti`
--
ALTER TABLE `utenti`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT per le tabelle scaricate
--

--
-- AUTO_INCREMENT per la tabella `faq`
--
ALTER TABLE `faq`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT per la tabella `logs`
--
ALTER TABLE `logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=29;

--
-- AUTO_INCREMENT per la tabella `utenti`
--
ALTER TABLE `utenti`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Limiti per le tabelle scaricate
--

--
-- Limiti per la tabella `logs`
--
ALTER TABLE `logs`
  ADD CONSTRAINT `logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `utenti` (`id`) ON DELETE SET NULL;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
