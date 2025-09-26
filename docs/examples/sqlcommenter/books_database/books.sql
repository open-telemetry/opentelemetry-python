-- MySQL dump for Books Database
-- Database: books_db
-- Generated on: 2025-08-29

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

-- Database: `books`
CREATE DATABASE IF NOT EXISTS `books` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `books`;

-- --------------------------------------------------------

-- Table structure for table `authors`

DROP TABLE IF EXISTS `authors`;
CREATE TABLE `authors` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `home_town` varchar(255) DEFAULT NULL,
  `birthdate` date DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `authors`

INSERT INTO `authors` (`id`, `name`, `home_town`, `birthdate`) VALUES
(1, 'Frank Herbert', 'Tacoma, Washington', '1920-10-08'),
(2, 'Isaac Asimov', 'Petrovichi, Russia', '1920-01-02'),
(3, 'Terry Pratchett', 'Beaconsfield, England', '1948-04-28');

-- --------------------------------------------------------

-- Table structure for table `books`

DROP TABLE IF EXISTS `books`;
CREATE TABLE `books` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `author_id` int(11) NOT NULL,
  `year_published` int(4) DEFAULT NULL,
  `genre` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_author` (`author_id`),
  CONSTRAINT `fk_author` FOREIGN KEY (`author_id`) REFERENCES `authors` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `books`

INSERT INTO `books` (`id`, `title`, `author_id`, `year_published`, `genre`) VALUES
(1, 'Dune', 1, 1965, 'Science Fiction'),
(2, 'Foundation', 2, 1951, 'Science Fiction'),
(3, 'The Colour of Magic', 3, 1983, 'Fantasy Comedy');

-- --------------------------------------------------------

-- Additional books to show the many-to-one relationship

INSERT INTO `books` (`id`, `title`, `author_id`, `year_published`, `genre`) VALUES
(4, 'Dune Messiah', 1, 1969, 'Science Fiction'),
(5, 'I, Robot', 2, 1950, 'Science Fiction'),
(6, 'Good Omens', 3, 1990, 'Fantasy Comedy');

-- --------------------------------------------------------

-- Auto increment values

ALTER TABLE `authors` AUTO_INCREMENT = 4;
ALTER TABLE `books` AUTO_INCREMENT = 7;

COMMIT;