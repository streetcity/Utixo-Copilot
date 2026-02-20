-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Creato il: Feb 20, 2026 alle 10:47
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
-- Struttura della tabella `conversations`
--

CREATE TABLE `conversations` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `title` varchar(120) NOT NULL DEFAULT 'Nuova chat',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dump dei dati per la tabella `conversations`
--

INSERT INTO `conversations` (`id`, `user_id`, `title`, `created_at`, `updated_at`) VALUES
(9, 4, 'ciao', '2026-02-20 08:30:00', '2026-02-20 08:30:00'),
(10, 4, 'chi seiii', '2026-02-20 08:30:10', '2026-02-20 08:30:10'),
(11, 4, 'ciao', '2026-02-20 09:41:27', '2026-02-20 09:42:02');

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
(12, 'generale', 'come pago una fattura utixo', 'Puoi pagare le fatture tramite PayPal, carta, bonifico o direttamente dall area clienti.', 'Per pagare una fattura accedi all area clienti Utixo e clicca su Paga accanto alla fattura.', 'Le fatture Utixo possono essere saldate nell area clienti usando carta, PayPal o bonifico.', '2025-12-05 11:45:23'),
(13, 'certificati SSL', 'Cos\'è un certificato wildcard e come generare un CSR?', 'Un certificato SSL wildcard protegge tutti i sottodomini di un dominio principale. Il Common Name (CN) assume la forma *.dominio.est, dove l\'asterisco rappresenta qualsiasi sottodominio.', 'Un certificato SSL wildcard consente di proteggere tutti i sottodomini di un dominio principale. Il campo Common Name (CN) viene indicato come *.dominio.est, dove l’asterisco indica che qualsiasi sottodominio sarà coperto.', 'Il certificato SSL wildcard tutela tutti i sottodomini di un dominio principale. Nel Common Name (CN) si utilizza la forma *.dominio.est, con l’asterisco che rappresenta qualsiasi sottodominio.', '2026-01-23 10:20:49'),
(14, 'certificati SSL', 'A cosa serve un CSR?', 'un CSR (Certificate Signing Request) contiene:\r\n\r\nLa chiave pubblica associata al certificato e le informazioni identificative dell\'azienda a cui verrà rilasciato.\r\nIl CSR viene solitamente generato direttamente dal sistema che userà il certificato. Tuttavia, se il servizio non consente la creazione automatica del CSR, è possibile generarlo manualmente seguendo questa procedura.', 'Un CSR (Certificate Signing Request) include la chiave pubblica collegata al certificato e i dati identificativi dell’organizzazione destinataria. Di norma, il CSR viene creato direttamente dal sistema che utilizzerà il certificato; se ciò non fosse possibile, può essere generato manualmente seguendo una procedura specifica.', 'Il CSR (Certificate Signing Request) contiene la chiave pubblica del certificato e le informazioni relative all’azienda che ne farà uso. Solitamente viene generato automaticamente dal sistema interessato, ma qualora il servizio non lo supporti, è possibile produrlo manualmente seguendo i passaggi indicati.', '2026-01-23 10:28:45'),
(15, 'certificati SSL', 'cosa posso fare con cPanel?', 'Il pannello di controllo cPanel consente l’attivazione automatica di certificati SSL gratuiti tramite Let’s Encrypt o il sistema AutoSSL integrato. In molti casi, questi certificati possono essere utilizzati senza alcun costo aggiuntivo.', 'Il pannello di gestione cPanel permette di attivare automaticamente certificati SSL gratuiti attraverso Let’s Encrypt o il sistema AutoSSL integrato. Spesso, questi certificati possono essere utilizzati senza costi aggiuntivi.', 'Con cPanel è possibile abilitare automaticamente certificati SSL gratuiti tramite Let’s Encrypt o AutoSSL. In numerosi casi, l’uso di questi certificati non comporta alcuna spesa extra.', '2026-01-23 10:28:08'),
(16, 'certificati SSL', 'Cos\'è una richiesta di firma del certificato?', 'Una CSR è uno dei primi passaggi necessari per ottenere un certificato SSL/TLS.\r\n\r\nViene generata sul server dove il certificato verrà installato e include informazioni che l’Autorità di Certificazione (CA) utilizzerà per emettere il certificato. Contiene inoltre la chiave pubblica che sarà inclusa nel certificato, firmata con la chiave privata corrispondente.', 'La CSR rappresenta uno dei primi step per ottenere un certificato SSL/TLS. Viene creata sul server destinato all’installazione del certificato e racchiude le informazioni che l’Autorità di Certificazione (CA) utilizzerà per emetterlo. Include inoltre la chiave pubblica che sarà parte del certificato, firmata con la chiave privata corrispondente.', 'Generare una CSR è uno dei passaggi iniziali per richiedere un certificato SSL/TLS. La CSR viene prodotta sul server in cui il certificato sarà installato e contiene i dati che la CA userà per rilasciarlo, insieme alla chiave pubblica da includere nel certificato, firmata con la chiave privata associata.', '2026-01-23 10:30:35'),
(17, 'certificati SSL', 'Quali informazioni contiene una CSR?', 'Una CSR include dati essenziali relativi all’organizzazione e al dominio da certificare. Tra le informazioni principali:\r\n\r\nCommon Name (CN): nome di dominio completo (FQDN) del server.\r\nOrganizzazione (O): nome legale completo dell’azienda, senza abbreviazioni né suffissi come Inc., Srl, ecc.\r\nUnità organizzativa (OU): reparto aziendale che gestisce il certificato.\r\nCittà/Località (L): città dove si trova l’azienda (senza abbreviazioni).\r\nStato/Regione (S): stato o provincia dell’organizzazione (senza abbreviazioni).\r\nPaese (C): codice a due lettere del Paese in cui ha sede l’azienda.\r\nEmail: indirizzo e-mail di contatto.\r\nOltre ai dati anagrafici, la CSR include anche:\r\n\r\nChiave pubblica: utilizzata per crittografare le comunicazioni.\r\nTipo e lunghezza della chiave: la più comune è RSA 2048, ma sono supportate anche RSA 4096 o chiavi ECC.', 'Una CSR contiene le informazioni fondamentali relative all’organizzazione e al dominio da certificare. Tra i principali campi troviamo:\r\n\r\nCommon Name (CN): nome di dominio completo (FQDN) del server.\r\n\r\nOrganizzazione (O): nome legale completo dell’azienda, senza abbreviazioni né suffissi come Inc., Srl, ecc.\r\n\r\nUnità organizzativa (OU): reparto aziendale responsabile del certificato.\r\n\r\nCittà/Località (L): città in cui ha sede l’azienda (senza abbreviazioni).\r\n\r\nStato/Regione (S): stato o provincia dell’organizzazione (senza abbreviazioni).\r\n\r\nPaese (C): codice a due lettere del Paese di appartenenza.\r\n\r\nEmail: indirizzo e-mail di contatto.\r\n\r\nOltre ai dati identificativi, la CSR include anche:\r\n\r\nChiave pubblica: usata per crittografare le comunicazioni.\r\n\r\nTipo e lunghezza della chiave: la più comune è RSA 2048, ma possono essere utilizzate anche chiavi RSA 4096 o ECC.', 'La CSR raccoglie i dati essenziali dell’organizzazione e del dominio da certificare. Tra le informazioni principali:\r\n\r\nCN (Common Name): dominio completo del server (FQDN).\r\n\r\nO (Organizzazione): nome legale completo dell’azienda, senza abbreviazioni o suffissi.\r\n\r\nOU (Unità organizzativa): reparto incaricato della gestione del certificato.\r\n\r\nL (Città/Località): città dell’azienda (nessuna abbreviazione).\r\n\r\nS (Stato/Regione): stato o provincia dell’organizzazione.\r\n\r\nC (Paese): codice a due lettere del Paese di residenza.\r\n\r\nEmail: contatto e-mail.\r\n\r\nLa CSR comprende anche:\r\n\r\nChiave pubblica: per crittografare le comunicazioni.\r\n\r\nTipo e dimensione della chiave: tipicamente RSA 2048, ma sono supportate anche RSA 4096 o chiavi ECC.', '2026-01-23 10:32:01'),
(18, 'certificati SSL', 'Qual è il formato di una CSR?', 'La CSR è generalmente generata in formato PEM (Base-64) e può essere aperta con un semplice editor di testo. Deve sempre includere l’intestazione e il piè di pagina:\r\n\r\n-----BEGIN CERTIFICATE REQUEST-----\r\n[contenuto codificato base64]\r\n-----END CERTIFICATE REQUEST-----\r\nEsempio reale:\r\n\r\n-----BEGIN CERTIFICATE REQUEST-----\r\nMIICvDCCAaQCAQAwdzELMAkGA1UEBhMCVVMxDTALBgNVBAgMBFV0YWgxDzANBgNV...\r\n...Uo39lBi1w=\r\n-----END CERTIFICATE REQUEST-----', 'La CSR viene solitamente generata in formato PEM (Base-64) e può essere visualizzata con un normale editor di testo. Deve sempre contenere l’intestazione e il piè di pagina:\r\n\r\n-----BEGIN CERTIFICATE REQUEST-----\r\n[contenuto codificato base64]\r\n-----END CERTIFICATE REQUEST-----\r\n\r\n\r\nEsempio concreto:\r\n\r\n-----BEGIN CERTIFICATE REQUEST-----\r\nMIICvDCCAaQCAQAwdzELMAkGA1UEBhMCVVMxDTALBgNVBAgMBFV0YWgxDzANBgNV...\r\n...Uo39lBi1w=\r\n-----END CERTIFICATE REQUEST-----', 'La CSR è generalmente prodotta in formato PEM (Base-64) e può essere aperta con qualsiasi editor di testo. È essenziale includere sempre l’intestazione e il footer:\r\n\r\n-----BEGIN CERTIFICATE REQUEST-----\r\n[contenuto codificato base64]\r\n-----END CERTIFICATE REQUEST-----\r\n\r\n\r\nEsempio reale di CSR:\r\n\r\n-----BEGIN CERTIFICATE REQUEST-----\r\nMIICvDCCAaQCAQAwdzELMAkGA1UEBhMCVVMxDTALBgNVBAgMBFV0YWgxDzANBgNV...\r\n...Uo39lBi1w=\r\n-----END CERTIFICATE REQUEST-----', '2026-01-23 10:33:42'),
(19, 'certificati SSL', 'Come generare una CSR?\r\n', 'La procedura varia in base al sistema operativo o al pannello di controllo utilizzato. Abbiamo guide dettagliate per le principali piattaforme, tra cui:\r\n\r\ncPanel/WHM\r\nMicrosoft Exchange\r\nIIS (Internet Information Services)\r\nJava Keytool\r\nOpenSSL (Linux/Unix)\r\nConsulta la guida relativa al tuo ambiente per generare correttamente il file CSR.', 'La procedura cambia a seconda del sistema operativo o del pannello di controllo in uso. Disponiamo di guide dettagliate per le principali piattaforme, tra cui:\r\n\r\ncPanel/WHM\r\n\r\nMicrosoft Exchange\r\n\r\nIIS (Internet Information Services)\r\n\r\nJava Keytool\r\n\r\nOpenSSL (Linux/Unix)\r\n\r\nSegui la guida specifica per il tuo ambiente per generare correttamente il file CSR.', 'La modalità di generazione del CSR dipende dal sistema operativo o dal pannello di controllo adottato. Per le piattaforme più comuni sono disponibili guide complete, tra cui:\r\n\r\ncPanel/WHM\r\n\r\nMicrosoft Exchange\r\n\r\nIIS (Internet Information Services)\r\n\r\nJava Keytool\r\n\r\nOpenSSL (Linux/Unix)\r\n\r\nConsulta la guida corrispondente al tuo ambiente per creare correttamente il CSR.', '2026-01-23 10:35:28'),
(20, 'certificati SSL', 'Come generare una richiesta CSR per Apache2?', 'Se stai utilizzando un server Apache2 senza pannello di controllo grafico (es. cPanel), puoi generare una richiesta di firma del certificato (CSR) direttamente da linea di comando tramite SSH.\r\n\r\n \r\n\r\n1. Accedi al server via SSH\r\nUtilizza un client SSH (come PuTTY o il terminale) per connetterti al server dove verrà installato il certificato SSL.\r\n\r\n \r\n\r\n2. Comando per generare CSR e chiave privata\r\nEsegui il seguente comando:\r\n\r\nopenssl req -new -newkey rsa:2048 -nodes -keyout domain.key -out domain.csr\r\nSostituisci domain con il nome del tuo dominio (es. esempio.com). Il comando genererà due file:\r\n\r\ndomain.key → chiave privata\r\ndomain.csr → richiesta CSR\r\n \r\n\r\n3. Inserisci le informazioni richieste\r\nDopo aver eseguito il comando, ti verranno richiesti alcuni dati. Compila come segue:\r\n\r\nCommon Name (CN): il nome di dominio completo (es. www.esempio.com)\r\nWildcard: per certificati jolly, inserisci *.esempio.com\r\nOrganization (O): nome legale dell\'azienda\r\nOrganizational Unit (OU): reparto o nome commerciale (facoltativo)\r\nCity/Locality (L): città (senza abbreviazioni)\r\nState/Province (S): provincia o regione (senza abbreviazioni)\r\nCountry (C): codice ISO a due lettere (es. IT per Italia)\r\n \r\n\r\n4. Copia e incolla la CSR nel modulo di richiesta SSL\r\nApri il file domain.csr con un editor di testo (es. nano, vim o scaricalo via FTP) e copia l’intero contenuto, inclusi intestazione e piè di pagina:\r\n\r\n-----BEGIN CERTIFICATE REQUEST-----\r\n[contenuto codificato]\r\n-----END CERTIFICATE REQUEST-----\r\nIncolla questo contenuto nel modulo di richiesta SSL nel tuo account Utixo o presso il fornitore scelto.', 'Se utilizzi un server Apache2 senza pannello grafico (ad esempio cPanel), puoi generare una CSR direttamente da linea di comando tramite SSH.\r\n\r\n1. Accedi al server via SSH\r\nConnettiti al server usando un client SSH (come PuTTY o il terminale) sul server dove installerai il certificato SSL.\r\n\r\n2. Genera CSR e chiave privata\r\nEsegui il comando:\r\n\r\nopenssl req -new -newkey rsa:2048 -nodes -keyout domain.key -out domain.csr\r\n\r\n\r\nSostituisci domain con il tuo dominio (es. esempio.com). Questo creerà due file:\r\n\r\ndomain.key → chiave privata\r\n\r\ndomain.csr → richiesta CSR\r\n\r\n3. Inserisci le informazioni richieste\r\nQuando il comando ti chiederà dei dati, compila come segue:\r\n\r\nCommon Name (CN): nome di dominio completo (es. www.esempio.com\r\n)\r\n\r\nWildcard: per certificati jolly, inserisci *.esempio.com\r\n\r\nOrganization (O): nome legale dell’azienda\r\n\r\nOrganizational Unit (OU): reparto o nome commerciale (facoltativo)\r\n\r\nCity/Locality (L): città (senza abbreviazioni)\r\n\r\nState/Province (S): provincia o regione (senza abbreviazioni)\r\n\r\nCountry (C): codice ISO a due lettere (es. IT)\r\n\r\n4. Copia la CSR nel modulo di richiesta SSL\r\nApri il file domain.csr con un editor di testo (nano, vim o tramite FTP) e copia tutto il contenuto, inclusi intestazione e piè di pagina:\r\n\r\n-----BEGIN CERTIFICATE REQUEST-----\r\n[contenuto codificato]\r\n-----END CERTIFICATE REQUEST-----\r\n\r\n\r\nIncolla poi questo contenuto nel modulo di richiesta SSL del tuo account Utixo o presso il provider scelto.', 'Per server Apache2 senza pannello di controllo grafico, la CSR può essere generata via SSH direttamente da terminale.\r\n\r\n1. Connessione al server\r\nUsa un client SSH (ad esempio PuTTY o terminale) per accedere al server dove installerai il certificato SSL.\r\n\r\n2. Comando per generare CSR e chiave privata\r\n\r\nopenssl req -new -newkey rsa:2048 -nodes -keyout domain.key -out domain.csr\r\n\r\n\r\nSostituisci domain con il tuo dominio reale. Il comando produrrà:\r\n\r\ndomain.key → chiave privata\r\n\r\ndomain.csr → richiesta di certificato\r\n\r\n3. Compila i dati richiesti\r\nInserisci le informazioni richieste dal comando:\r\n\r\nCN (Common Name): dominio completo (es. www.esempio.com\r\n)\r\n\r\nWildcard: *.esempio.com per certificati jolly\r\n\r\nO (Organization): nome legale dell’azienda\r\n\r\nOU (Organizational Unit): reparto o nome commerciale (facoltativo)\r\n\r\nL (City/Locality): città (senza abbreviazioni)\r\n\r\nS (State/Province): provincia o regione (senza abbreviazioni)\r\n\r\nC (Country): codice ISO a due lettere (es. IT)\r\n\r\n4. Inserisci la CSR nel modulo SSL\r\nApri domain.csr con un editor di testo o scaricalo via FTP e copia l’intero contenuto, intestazione e piè di pagina inclusi:\r\n\r\n-----BEGIN CERTIFICATE REQUEST-----\r\n[contenuto codificato]\r\n-----END CERTIFICATE REQUEST-----\r\n\r\n\r\nIncolla il contenuto nel modulo di richiesta SSL del tuo provider o del tuo account Utixo.', '2026-01-23 10:37:24'),
(21, 'certificati SSL', 'Come posso installareun certificato SSL su GlassFish?', 'Apri la console dei comandi (cmd) e accedi alla cartella config del dominio GlassFish. Esempio:\r\n\r\ncd glassfish4\\glassfish\\domains\\domain1\\config\r\n \r\n\r\n1. Creazione della chiave (solo per prima installazione)\r\nSe non è già presente una chiave nel keystore, esegui il seguente comando per crearla:\r\n\r\nkeytool -genkey -alias nomeAlias -keyalg RSA -keysize 2048 -keystore keystore.jks -noprompt -v -dname \"CN=dominio,O=società,OU=proprietario,L=città,S=nazione,C=siglaNazione\" -storepass changeit\r\nSostituisci nomeAlias con un identificativo del dominio, ad esempio senza punti (esempiocom).\r\n\r\n \r\n\r\n2. Generazione della CSR\r\nPer richiedere un certificato, genera la CSR con il comando:\r\n\r\nkeytool -certreq -alias nomeAlias -file nomeAlias.csr -keystore keystore.jks -storepass changeit\r\nCarica la CSR nel control panel Utixo e scegli un metodo di validazione (email o DNS).\r\n\r\n \r\n\r\n3a. Importazione certificati (formato CRT separato)\r\nSe hai ricevuto i certificati in formato singolo (root, intermediate, dominio):\r\n\r\nPulisci i certificati precedenti\r\nkeytool -delete -alias root -keystore keystore.jks -storepass changeit\r\nkeytool -delete -alias intermed -keystore keystore.jks -storepass changeit\r\nkeytool -delete -alias root -keystore cacerts.jks -storepass changeit\r\nkeytool -delete -alias intermed -keystore cacerts.jks -storepass changeit\r\nImporta root, intermedi e certificato dominio\r\nkeytool -import -trustcacerts -alias root -file AAACertificateServices.crt -keystore keystore.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias intermed -file USERTrustRSAAAACA.crt -keystore keystore.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias SectigoRSADomainValidationSecureServerCA -file SectigoRSADomainValidationSecureServerCA.crt -keystore keystore.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias nomeAlias -file nomeAlias.crt -keystore keystore.jks -storepass changeit\r\n\r\nkeytool -import -trustcacerts -alias root -file AAACertificateServices.crt -keystore cacerts.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias intermed -file USERTrustRSAAAACA.crt -keystore cacerts.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias SectigoRSADomainValidationSecureServerCA -file SectigoRSADomainValidationSecureServerCA.crt -keystore cacerts.jks -storepass changeit\r\n \r\n\r\n3b. Importazione certificati (CA Bundle o P7B)\r\nSe hai ricevuto un file .ca-bundle o .p7b, procedi così:\r\n\r\nPulisci i certificati precedenti\r\nkeytool -delete -alias cabundle -keystore keystore.jks -storepass changeit\r\nkeytool -delete -alias cabundle -keystore cacerts.jks -storepass changeit\r\nImporta bundle e certificato dominio\r\nkeytool -import -trustcacerts -alias cabundle -file nomeAlias.ca-bundle -keystore keystore.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias nomeAlias -file nomeAlias.crt -keystore keystore.jks -storepass changeit\r\noppure:\r\n\r\nkeytool -import -trustcacerts -alias nomeAlias -file nomeAlias.p7b -keystore keystore.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias cabundle -file nomeAlias.ca-bundle -keystore cacerts.jks -storepass changeit\r\n \r\n\r\n4. Verifica dell\'importazione\r\nkeytool -list -alias nomeAlias -keystore keystore.jks -storepass changeit\r\n \r\n\r\n5. Associare il certificato in GlassFish\r\nAccedi alla console GlassFish e vai su:\r\n\r\nConfigurazioni → server-config → Servizio HTTP → Listener HTTP → http-listener-2 → SSL\r\n\r\nInserisci nomeAlias nella casella Alias certificato per attivarlo.\r\n\r\n \r\n\r\n6. Riavviare GlassFish\r\nRiavvia il server GlassFish per applicare le modifiche e rendere attivo il nuovo certificato SSL.', 'Apri il prompt dei comandi (cmd) e posizionati nella cartella config del dominio GlassFish, ad esempio:\r\n\r\ncd glassfish4\\glassfish\\domains\\domain1\\config\r\n\r\n\r\n1. Creazione della chiave (solo al primo setup)\r\nSe non è presente una chiave nel keystore, esegui:\r\n\r\nkeytool -genkey -alias nomeAlias -keyalg RSA -keysize 2048 -keystore keystore.jks -noprompt -v -dname \"CN=dominio,O=società,OU=proprietario,L=città,S=nazione,C=siglaNazione\" -storepass changeit\r\n\r\n\r\nSostituisci nomeAlias con un identificativo del dominio, senza punti (es. esempiocom).\r\n\r\n2. Generazione della CSR\r\nPer richiedere il certificato, crea la CSR:\r\n\r\nkeytool -certreq -alias nomeAlias -file nomeAlias.csr -keystore keystore.jks -storepass changeit\r\n\r\n\r\nCarica il file .csr nel control panel Utixo e scegli il metodo di validazione (email o DNS).\r\n\r\n3a. Importazione certificati separati (CRT)\r\nSe hai ricevuto certificati separati (root, intermedi, dominio):\r\n\r\nElimina certificati precedenti\r\n\r\nkeytool -delete -alias root -keystore keystore.jks -storepass changeit\r\nkeytool -delete -alias intermed -keystore keystore.jks -storepass changeit\r\nkeytool -delete -alias root -keystore cacerts.jks -storepass changeit\r\nkeytool -delete -alias intermed -keystore cacerts.jks -storepass changeit\r\n\r\n\r\nImporta root, intermedi e certificato dominio\r\n\r\nkeytool -import -trustcacerts -alias root -file AAACertificateServices.crt -keystore keystore.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias intermed -file USERTrustRSAAAACA.crt -keystore keystore.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias SectigoRSADomainValidationSecureServerCA -file SectigoRSADomainValidationSecureServerCA.crt -keystore keystore.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias nomeAlias -file nomeAlias.crt -keystore keystore.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias root -file AAACertificateServices.crt -keystore cacerts.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias intermed -file USERTrustRSAAAACA.crt -keystore cacerts.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias SectigoRSADomainValidationSecureServerCA -file SectigoRSADomainValidationSecureServerCA.crt -keystore cacerts.jks -storepass changeit\r\n\r\n\r\n3b. Importazione certificati in bundle (.ca-bundle o .p7b)\r\n\r\nElimina bundle precedenti\r\n\r\nkeytool -delete -alias cabundle -keystore keystore.jks -storepass changeit\r\nkeytool -delete -alias cabundle -keystore cacerts.jks -storepass changeit\r\n\r\n\r\nImporta bundle e certificato dominio\r\n\r\nkeytool -import -trustcacerts -alias cabundle -file nomeAlias.ca-bundle -keystore keystore.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias nomeAlias -file nomeAlias.crt -keystore keystore.jks -storepass changeit\r\n\r\n\r\noppure:\r\n\r\nkeytool -import -trustcacerts -alias nomeAlias -file nomeAlias.p7b -keystore keystore.jks -storepass changeit\r\nkeytool -import -trustcacerts -alias cabundle -file nomeAlias.ca-bundle -keystore cacerts.jks -storepass changeit\r\n\r\n\r\n4. Verifica dell’importazione\r\n\r\nkeytool -list -alias nomeAlias -keystore keystore.jks -storepass changeit\r\n\r\n\r\n5. Associare il certificato in GlassFish\r\nAccedi alla console GlassFish:\r\n\r\nConfigurazioni → server-config → Servizio HTTP → Listener HTTP → http-listener-2 → SSL\r\n\r\n\r\nInserisci nomeAlias nella casella “Alias certificato” per attivarlo.\r\n\r\n6. Riavvia GlassFish\r\nRiavvia il server per applicare le modifiche e rendere operativo il nuovo certificato SSL.', 'Apri cmd e vai nella cartella config\r\n\r\ncd glassfish4\\glassfish\\domains\\domain1\\config\r\n\r\n\r\nCrea chiave (solo al primo setup)\r\n\r\nkeytool -genkey -alias nomeAlias -keyalg RSA -keysize 2048 -keystore keystore.jks -noprompt -v -dname \"CN=dominio,O=società,OU=proprietario,L=città,S=nazione,C=siglaNazione\" -storepass changeit\r\n\r\n\r\nGenera CSR\r\n\r\nkeytool -certreq -alias nomeAlias -file nomeAlias.csr -keystore keystore.jks -storepass changeit\r\n\r\n\r\nCarica il .csr su Utixo e seleziona il metodo di validazione.\r\n\r\nImporta certificati\r\n\r\nSe CRT separati: elimina vecchi certificati e importa root, intermedi e dominio.\r\n\r\nSe CA bundle (.ca-bundle o .p7b): elimina vecchi bundle e importa nuovo bundle e certificato dominio.\r\n\r\nVerifica importazione\r\n\r\nkeytool -list -alias nomeAlias -keystore keystore.jks -storepass changeit\r\n\r\n\r\nAssociare certificato in GlassFish\r\nConsole → Configurazioni → server-config → Servizio HTTP → Listener HTTP → http-listener-2 → SSL → inserisci alias.\r\n\r\nRiavvia GlassFish\r\nPer rendere attivo il certificato SSL.', '2026-01-23 10:40:23'),
(22, 'certificati SSL', 'Che cos\'è il controllo CAA?', 'Il controllo CAA (Certificate Authority Authorization) è un meccanismo di sicurezza basato su DNS che consente ai proprietari di un dominio di specificare quali Autorità di Certificazione (CA) sono autorizzate a emettere certificati SSL/TLS per quel dominio.\r\n\r\nConfigurando un record CAA all’interno del DNS del proprio dominio, è possibile limitare l’emissione dei certificati solo ad alcune CA specifiche. Questo riduce il rischio che una CA non autorizzata rilasci un certificato fraudolento o non conforme.\r\n\r\nAd esempio, se si desidera autorizzare solo sectigo.com come CA, si può configurare un record come il seguente:\r\n\r\nexample.com.  CAA  0 issue \"sectigo.com\"\r\n\r\nUn CAA:\r\nAumenta la sicurezza del dominio contro emissioni non autorizzate\r\nÈ supportato da tutte le CA principali e considerato uno standard di buona pratica\r\nÈ raccomandato per i domini pubblici che richiedono certificati SSL/TLS\r\n\r\nQuando una CA riceve una richiesta per emettere un certificato SSL/TLS, esegue una query DNS sul record CAA del dominio. Se non trova il proprio nome all’interno del record, rifiuterà la richiesta di certificato.', 'Il controllo CAA (Certificate Authority Authorization) è un meccanismo di sicurezza basato su DNS che permette ai proprietari di un dominio di indicare quali Autorità di Certificazione (CA) sono autorizzate a emettere certificati SSL/TLS per quel dominio.\r\n\r\nConfigurando un record CAA nel DNS del proprio dominio, si limita l’emissione dei certificati solo alle CA specificate, riducendo il rischio di certificati emessi da CA non autorizzate o fraudolente.\r\n\r\nAd esempio, per autorizzare solo sectigo.com come CA:\r\n\r\nexample.com.  CAA  0 issue \"sectigo.com\"\r\n\r\n\r\nVantaggi del CAA:\r\n\r\nAumenta la sicurezza del dominio contro emissioni non autorizzate\r\n\r\nSupportato da tutte le principali CA ed è considerato una best practice\r\n\r\nRaccomandato per domini pubblici che richiedono certificati SSL/TLS\r\n\r\nQuando una CA riceve una richiesta di certificato, verifica il record CAA del dominio tramite DNS. Se il proprio nome non è presente, la richiesta viene rifiutata.', 'Il CAA (Certificate Authority Authorization) è un record DNS che consente ai proprietari di dominio di specificare quali CA possono emettere certificati SSL/TLS per il loro dominio.\r\n\r\nConfigurando correttamente il CAA, si impedisce a CA non autorizzate di rilasciare certificati, aumentando la sicurezza.\r\n\r\nEsempio per autorizzare solo sectigo.com:\r\n\r\nexample.com.  CAA  0 issue \"sectigo.com\"\r\n\r\n\r\nPunti chiave:\r\n\r\nProtegge il dominio da emissioni di certificati non autorizzate\r\n\r\nSupportato da tutte le principali CA\r\n\r\nRaccomandato per domini pubblici che richiedono SSL/TLS\r\n\r\nQuando una CA riceve una richiesta di certificato, controlla il record CAA tramite DNS e rifiuta la richiesta se il suo nome non è autorizzato.', '2026-01-23 10:43:19');

-- --------------------------------------------------------

--
-- Struttura della tabella `logs`
--

CREATE TABLE `logs` (
  `id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `conversation_id` int(11) DEFAULT NULL,
  `messaggio_utente` text NOT NULL,
  `risposta_bot` text DEFAULT NULL,
  `similarity` float DEFAULT NULL,
  `faq_id` int(11) DEFAULT NULL,
  `resolved` tinyint(1) NOT NULL DEFAULT 0,
  `data_ora` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dump dei dati per la tabella `logs`
--

INSERT INTO `logs` (`id`, `user_id`, `conversation_id`, `messaggio_utente`, `risposta_bot`, `similarity`, `faq_id`, `resolved`, `data_ora`) VALUES
(48, NULL, NULL, 'ciao', 'Salve! In cosa posso esserti utile?', 1, 1, 1, '2026-02-20 08:14:07'),
(49, 4, NULL, 'ciao chatbot', 'Salve! In cosa posso esserti utile?', 0.661562, 1, 1, '2026-02-20 08:16:19'),
(50, 4, 9, 'ciao', 'Ciao! Hai bisogno di assistenza?', 1, 1, 1, '2026-02-20 08:30:00'),
(51, 4, 10, 'chi seiii', 'Non ho trovato una risposta precisa.', 0, NULL, 0, '2026-02-20 08:30:10'),
(52, 4, 11, 'ciao', 'Salve! In cosa posso esserti utile?', 1, 1, 1, '2026-02-20 09:41:27'),
(53, 4, 11, 'ciao bello', 'Ciao! Come posso aiutarti?', 0.661562, 1, 1, '2026-02-20 09:41:30'),
(54, 4, 11, 'come va?', 'Non ho trovato una risposta precisa.', 0, NULL, 0, '2026-02-20 09:41:32'),
(55, 4, 11, 'ciao chi sei?', 'Salve! In cosa posso esserti utile?', 1, 1, 1, '2026-02-20 09:42:02'),
(56, NULL, NULL, 'ciao', 'Ciao! Hai bisogno di assistenza?', 1, 1, 1, '2026-02-20 09:42:29'),
(57, NULL, NULL, 'chatbot', 'Non ho trovato una risposta precisa.', 0, NULL, 0, '2026-02-20 09:42:31'),
(58, NULL, NULL, 'miao miao', 'Non ho trovato una risposta precisa.', 0, NULL, 0, '2026-02-20 09:42:35');

-- --------------------------------------------------------

--
-- Struttura della tabella `utenti`
--

CREATE TABLE `utenti` (
  `id` int(11) NOT NULL,
  `nome` varchar(100) DEFAULT NULL,
  `password` varchar(255) NOT NULL,
  `email` varchar(150) DEFAULT NULL,
  `data_creazione` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dump dei dati per la tabella `utenti`
--

INSERT INTO `utenti` (`id`, `nome`, `password`, `email`, `data_creazione`) VALUES
(3, 'admin', 'scrypt:32768:8:1$9xVkxmqzbvDmUu7A$0ae78bf3ca45a8450dc523f4652fae30e6b42c84ef8fa7b9f873b541b14a5e7dcb5a881afd0e4fa47ee532ea6679afc078ff88a4fd111aa8d87c5113e11ec847', 'tec1@utixo.net', '2026-02-12 23:00:00'),
(4, 'fusar', 'scrypt:32768:8:1$SbxUB9GOxtxDuWX0$6d50aec0bdf952fe0be364146e8f3f1fa6e6f59b08128c20e7e3c9964cead65a0d656eb798f0f03709bfa65090519bebee2211ede9263aebc5fb463459debe89', 'simofusar@gmail.com', '2026-02-20 08:15:59');

--
-- Indici per le tabelle scaricate
--

--
-- Indici per le tabelle `conversations`
--
ALTER TABLE `conversations`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_conv_user_updated` (`user_id`,`updated_at`);

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
  ADD KEY `user_id` (`user_id`),
  ADD KEY `idx_logs_user_conv_id` (`user_id`,`conversation_id`,`id`),
  ADD KEY `fk_logs_conversation` (`conversation_id`);

--
-- Indici per le tabelle `utenti`
--
ALTER TABLE `utenti`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_utenti_nome` (`nome`),
  ADD UNIQUE KEY `uq_utenti_email` (`email`);

--
-- AUTO_INCREMENT per le tabelle scaricate
--

--
-- AUTO_INCREMENT per la tabella `conversations`
--
ALTER TABLE `conversations`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT per la tabella `faq`
--
ALTER TABLE `faq`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=25;

--
-- AUTO_INCREMENT per la tabella `logs`
--
ALTER TABLE `logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=59;

--
-- AUTO_INCREMENT per la tabella `utenti`
--
ALTER TABLE `utenti`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- Limiti per le tabelle scaricate
--

--
-- Limiti per la tabella `conversations`
--
ALTER TABLE `conversations`
  ADD CONSTRAINT `fk_conv_user` FOREIGN KEY (`user_id`) REFERENCES `utenti` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Limiti per la tabella `logs`
--
ALTER TABLE `logs`
  ADD CONSTRAINT `fk_logs_conversation` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  ADD CONSTRAINT `logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `utenti` (`id`) ON DELETE SET NULL;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
